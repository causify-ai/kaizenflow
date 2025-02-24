"""
Import as:

import dataflow.core.result_bundle as dtfcorebun
"""
import abc
import collections
import copy
import datetime
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, cast

import pandas as pd

import core.config as cconfig
import dataflow.core.node as dtfcornode
import helpers.hdbg as hdbg
import helpers.hgit as hgit
import helpers.hio as hio
import helpers.hparquet as hparque
import helpers.hpickle as hpickle
import helpers.htimer as htimer

_LOG = logging.getLogger(__name__)


# #############################################################################
# ResultBundle
# #############################################################################


class ResultBundle(abc.ABC):
    """
    Abstract class for storing `DAG` execution results.
    """

    def __init__(
        self,
        config: cconfig.Config,
        result_nid: dtfcornode.NodeId,
        method: dtfcornode.Method,
        result_df: pd.DataFrame,
        # TODO(gp): -> str
        column_to_tags: Optional[Dict[Any, List[Any]]] = None,
        info: Optional[collections.OrderedDict] = None,
        payload: Optional[cconfig.Config] = None,
    ) -> None:
        """
        Constructor.

        :param config: DAG config
        :param result_nid: identifier of terminal node for which DAG was executed
        :param method: method which was executed
        :param result_df: dataframe with results
        :param column_to_tags: mapping of column names to list of tags. E.g.,
            `{"y.shift_-0": ["target_col", "step_0"], ...}`
        :param info: DAG execution info
        :param payload: config with additional information, e.g., meta config
        """
        hdbg.dassert_isinstance(config, cconfig.Config)
        self._config = config
        self._result_nid = result_nid
        hdbg.dassert_isinstance(method, dtfcornode.Method)
        self._method = method
        if result_df is not None:
            # TODO(Grisha): consider using `dassert_is_result_df()`; now some
            # tests fail, see CmTask3515.
            hdbg.dassert_isinstance(result_df, pd.DataFrame)
        self._result_df = result_df
        if isinstance(column_to_tags, cconfig.Config):
            # It should be a dict but when we initialize `ResultBundle` using a config,
            # e.g., `ResultBundle(**config)` the value is a config because dict-like
            # values are not allowed.
            column_to_tags = column_to_tags.to_dict()
        self._column_to_tags = column_to_tags
        self._info = info
        self._payload = payload

    # ///////////////////////////////////////////////////////////////////////////
    # Print.
    # ///////////////////////////////////////////////////////////////////////////

    def __str__(self) -> str:
        """
        Return a string representation.
        """
        return str(self.to_config())

    def __repr__(self) -> str:
        """
        Return an unambiguous string representation.

        This is used by Jupyter notebook when printing.
        """
        return str(self)

    # ///////////////////////////////////////////////////////////////////////////
    # Virtual constructors.
    # ///////////////////////////////////////////////////////////////////////////

    # TODO(gp): Use `@classmethod`.
    @staticmethod
    def from_dict(result_bundle_dict: collections.OrderedDict) -> "ResultBundle":
        """
        Initialize `ResultBundle` from a nested dict.
        """
        result_bundle_config = cconfig.Config.from_dict(result_bundle_dict)
        result_bundle_class = eval(result_bundle_config["class"])
        result_bundle: ResultBundle = result_bundle_class.from_config(
            result_bundle_config
        )
        return result_bundle

    # TODO(gp): Use `@classmethod`.
    @staticmethod
    def from_pickle(
        file_name: str,
        use_pq: bool = True,
        columns: Optional[List[str]] = None,
    ) -> "ResultBundle":
        """
        Deserialize the current `ResultBundle`.

        :param file_name: name of the file to load
        :param use_pq: load multiple files storing the data
        :param columns: columns of `result_df` to load
        """
        # TODO(gp): We should pass file_name without an extension, since the
        #  extension(s) depend on the format used.
        if use_pq:
            # Load the part of the `ResultBundle` stored as pickle.
            hdbg.dassert(
                file_name.endswith("v2_0.pkl"),
                "Invalid file_name='%s'",
                file_name,
            )
            with htimer.TimedScope(logging.DEBUG, "Load pickle"):
                obj = hpickle.from_pickle(file_name, log_level=logging.DEBUG)
                # TODO(gp): This is a workaround waiting for LimeTask164.
                #  We load 200MB of data and then discard 198MB.
                if hasattr(obj, "payload"):
                    obj.payload = None
                hdbg.dassert_isinstance(obj, ResultBundle)
            # Load the `result_df` as parquet.
            file_name_pq = hio.change_filename_extension(file_name, "pkl", "pq")
            if columns is None:
                _LOG.warning(
                    "Loading the entire `result_df` without filtering by columns: "
                    "this is slow and requires a lot of memory"
                )
            with htimer.TimedScope(logging.DEBUG, "Load parquet"):
                obj.result_df = hparque.from_parquet(
                    file_name_pq, columns=columns, log_level=logging.DEBUG
                )
            file_name_metadata_df = hio.change_filename_extension(
                file_name, "pkl", "metadata_df.pkl"
            )
            metadata_df = hpickle.from_pickle(
                file_name_metadata_df, log_level=logging.DEBUG
            )
            # metadata_df = {
            #     "index.freq": result_df.index.freq
            # }
            obj.result_df.index.freq = metadata_df.pop("index.freq")
            # TODO(gp): See AmpTask1732 about disabling this.
            # obj.result_df = _trim_df_trading_hours(obj.result_df)
            hdbg.dassert(
                not metadata_df, "metadata_df='%s' is not empty", str(metadata_df)
            )
        else:
            # Load the `ResultBundle` as a single pickle.
            hdbg.dassert(
                file_name.endswith("v1_0.pkl"),
                "Invalid file_name='%s'",
                file_name,
            )
            hdbg.dassert_is(
                columns,
                None,
                "`columns` can be specified only with `use_pq=True`",
            )
            file_name = hio.change_filename_extension(
                file_name, "pkl", "v1_0.pkl"
            )
            obj = hpickle.from_pickle(file_name, log_level=logging.DEBUG)
        return obj  # type: ignore

    # //////////////////////////////////////////////////////////////////////////
    # Accessors.
    # //////////////////////////////////////////////////////////////////////////

    @property
    def config(self) -> cconfig.Config:
        return self._config

    @property
    def result_nid(self) -> dtfcornode.NodeId:
        return self._result_nid

    @property
    def method(self) -> dtfcornode.Method:
        return self._method

    @property
    def result_df(self) -> pd.DataFrame:
        return self._result_df

    @property
    def column_to_tags(self) -> Optional[Dict[Any, List[Any]]]:
        return copy.deepcopy(self._column_to_tags)

    @property
    def tag_to_columns(self) -> Optional[Dict[Any, List[Any]]]:
        if self._column_to_tags is not None:
            # TODO(gp): Cache it or compute it the first time.
            tag_to_columns: Dict[Any, List[Any]] = {}
            for column, tags in self._column_to_tags.items():
                for tag in tags:
                    tag_to_columns.setdefault(tag, []).append(column)
            return tag_to_columns
        return None

    @property
    def info(self) -> Optional[collections.OrderedDict]:
        if self._info is not None:
            return self._info.copy()
        return None

    @property
    def payload(self) -> Optional[cconfig.Config]:
        return self._payload

    def get_tags_for_column(self, column: Any) -> Optional[List[Any]]:
        return ResultBundle._search_mapping(column, self._column_to_tags)

    def get_columns_for_tag(self, tag: Any) -> Optional[List[Any]]:
        return ResultBundle._search_mapping(tag, self.tag_to_columns)

    # //////////////////////////////////////////////////////////////////////////
    # Setters.
    # //////////////////////////////////////////////////////////////////////////

    @result_df.setter  # type: ignore
    def result_df(self, value: pd.DataFrame) -> None:
        self._result_df = value

    @payload.setter  # type: ignore
    def payload(self, value: Optional[cconfig.Config]) -> None:
        self._payload = value

    # //////////////////////////////////////////////////////////////////////////
    # Serialize to / from strings.
    # //////////////////////////////////////////////////////////////////////////

    # TODO(gp): Not sure if all the serialization would work also for derived classes,
    #  e.g., `PredictionResultBundle`.

    def to_config(self, commit_hash: bool = False) -> cconfig.Config:
        """
        Represent class state as config.

        :param commit_hash: whether to include current commit hash
        """
        serialized_bundle = {}
        serialized_bundle["config"] = self._config
        serialized_bundle["result_nid"] = self._result_nid
        serialized_bundle["method"] = self._method
        serialized_bundle["result_df"] = self._result_df
        serialized_bundle["column_to_tags"] = self._column_to_tags
        info = self._info
        serialized_bundle["info"] = info
        serialized_bundle["payload"] = self._payload
        serialized_bundle["class"] = self.__class__.__name__
        if commit_hash:
            serialized_bundle["commit_hash"] = hgit.get_current_commit_hash()
        # Convert to a `Config`.
        serialized_bundle = cconfig.Config.from_dict(serialized_bundle)
        return serialized_bundle

    @classmethod
    def from_config(cls, serialized_bundle: cconfig.Config) -> "ResultBundle":
        """
        Initialize `ResultBundle` from config.
        """
        # In a `Config` dicts are configs but the class accepts `info` and
        # `column_to_tags` as dicts.
        column_to_tags = serialized_bundle["column_to_tags"]
        if column_to_tags:
            column_to_tags = column_to_tags.to_dict()
        info = serialized_bundle["info"]
        if info:
            info = info.to_dict()
        rb = cls(
            config=serialized_bundle["config"],
            result_nid=serialized_bundle["result_nid"],
            method=serialized_bundle["method"],
            result_df=serialized_bundle["result_df"],
            column_to_tags=column_to_tags,
            info=info,
            payload=serialized_bundle["payload"],
        )
        return rb

    def to_dict(self, commit_hash: bool = False) -> collections.OrderedDict:
        """
        Represent class state as an ordered dict.
        """
        config = self.to_config(commit_hash=commit_hash)
        dict_ = config.to_dict()
        dict_ = cast(collections.OrderedDict, dict_)
        return dict_

    # //////////////////////////////////////////////////////////////////////////
    # Serialize to / from disk.
    # //////////////////////////////////////////////////////////////////////////

    def to_pickle(self, file_name: str, use_pq: bool = True) -> List[str]:
        """
        Serialize the current `ResultBundle`.

        :param file_name: file to save
        :param use_pq: save the `result_df` dataframe using Parquet.
            If False, everything is saved as a single pickle object.
        :return: list with names of the files saved
        """
        # TODO(gp): We should pass file_name without an extension, since the
        #  extension(s) depend on the format used.
        hio.create_enclosing_dir(file_name, incremental=True)
        # Convert to a dict.
        obj = copy.copy(self)
        if use_pq:
            # Split the object in two pieces.
            result_df = obj.result_df
            obj.result_df = None  # type: ignore
            # Save the config as pickle.
            file_name_rb = hio.change_filename_extension(
                file_name, "pkl", "v2_0.pkl"
            )
            hpickle.to_pickle(obj, file_name_rb, log_level=logging.DEBUG)
            # Save the `result_df` as parquet.
            file_name_pq = hio.change_filename_extension(
                file_name, "pkl", "v2_0.pq"
            )
            hparque.to_parquet(result_df, file_name_pq, log_level=logging.DEBUG)
            file_name_metadata_df = hio.change_filename_extension(
                file_name, "pkl", "v2_0.metadata_df.pkl"
            )
            metadata_df = {"index.freq": result_df.index.freq}
            hpickle.to_pickle(
                metadata_df, file_name_metadata_df, log_level=logging.DEBUG
            )
            #
            res = [file_name_rb, file_name_pq, file_name_metadata_df]
        else:
            # Save the entire object as pickle.
            file_name = hio.change_filename_extension(
                file_name, "pkl", "v1_0.pkl"
            )
            hpickle.to_pickle(obj, file_name, log_level=logging.DEBUG)
            res = [file_name]
        return res

    @staticmethod
    def _search_mapping(
        key: Any, mapping: Optional[Dict[Any, List[Any]]]
    ) -> Optional[List[Any]]:
        """
        Look for a key `key` in the dictionary `mapping`.

        Return the corresponding value or `None` if the key does not
        exist.
        """
        if mapping is None:
            _LOG.warning("No mapping provided to search for '%s'", key)
            return None
        if key not in mapping:
            _LOG.warning("'%s' not in `mapping`='%s'", key, mapping)
            return None
        return mapping[key]


# #############################################################################
# PredictionResultBundle
# #############################################################################


class PredictionResultBundle(ResultBundle):
    """
    Class adding some semantic meaning to a `ResultBundle`.
    """

    @property
    def feature_col_names(self) -> List[Any]:
        cols = self.get_columns_for_tag("feature_col") or []
        return cols

    @property
    def target_col_names(self) -> List[Any]:
        cols = self.get_columns_for_tag("target_col") or []
        return cols

    @property
    def prediction_col_names(self) -> List[Any]:
        cols = self.get_columns_for_tag("prediction_col") or []
        return cols

    def get_target_and_prediction_col_names_for_tags(
        self, tags: List[Any]
    ) -> Dict[Any, Tuple[Any, Any]]:
        """
        Get target and prediction column names for tags.

        :param tags: list of tags
        :return: `Dict[tag, NamedTuple[target_col_name, prediction_col_name]]`,
            `NamedTuple` field names are "target" and "prediction"
        """
        hdbg.dassert_isinstance(tags, list)
        target_cols = set(self.target_col_names)
        prediction_cols = set(self.prediction_col_names)
        # TODO(gp): Move this out.
        TargetPredictionColPair = collections.namedtuple(
            "TargetPredictionColPair", ["target", "prediction"]
        )
        tags_to_target_and_prediction_cols: Dict[Any, Tuple[Any, Any]] = {}
        for tag in tags:
            cols_for_tag = self.get_columns_for_tag(tag) or []
            target_cols_for_tag = self._get_intersection_with_cols_for_tag(
                target_cols, cols_for_tag, "target", tag
            )
            prediction_cols_for_tag = self._get_intersection_with_cols_for_tag(
                prediction_cols, cols_for_tag, "prediction", tag
            )
            target_prediction_col_pair = TargetPredictionColPair(
                target=target_cols_for_tag,
                prediction=prediction_cols_for_tag,
            )
            tags_to_target_and_prediction_cols[tag] = target_prediction_col_pair
        return tags_to_target_and_prediction_cols

    @property
    def features(self) -> pd.DataFrame:
        return self.result_df[self.feature_col_names]

    @property
    def targets(self) -> pd.DataFrame:
        return self.result_df[self.target_col_names]

    @property
    def predictions(self) -> pd.DataFrame:
        return self.result_df[self.prediction_col_names]

    def get_targets_and_predictions_for_tags(
        self, tags: List[Any]
    ) -> Dict[Any, Tuple[pd.Series, pd.Series]]:
        """
        Get target and prediction series for tags.

        :param tags: list of tags
        :return: `Dict[tag, NamedTuple[target_series, prediction_series]]`,
            `NamedTuple` field names are "target" and "prediction"
        """
        tags_to_target_and_prediction_cols = (
            self.get_target_and_prediction_col_names_for_tags(tags)
        )
        TargetPredictionPair = collections.namedtuple(
            "TargetPredictionPair", ["target", "prediction"]
        )
        targets_and_predictions_for_tags: Dict[
            Any, Tuple[pd.Series, pd.Series]
        ] = {}
        for tag, (
            target_col,
            prediction_col,
        ) in tags_to_target_and_prediction_cols.items():
            target_prediction_pair = TargetPredictionPair(
                target=self.result_df[target_col],
                prediction=self.result_df[prediction_col],
            )
            targets_and_predictions_for_tags[tag] = target_prediction_pair
        return targets_and_predictions_for_tags

    @staticmethod
    def _get_intersection_with_cols_for_tag(
        selected_cols: Set[Any],
        cols_for_tag: List[Any],
        selected_type: str,
        tag: Any,
    ) -> Any:
        """
        Get intersection of `selected_cols` and `cols_for_tag`.

        :param selected_cols: set of columns
        :param cols_for_tag: list of columns for tag
        :param selected_type: type of `selected_cols`, typically "target" or
            "prediction". Used for the assertion message
        :param tag: tag of `cols_for_tag`. Used for the assertion message
        :return: intersection of `selected_cols` and `cols_for_tag`
        """
        selected_cols_for_tag = list(selected_cols.intersection(cols_for_tag))
        hdbg.dassert_eq(
            len(selected_cols_for_tag),
            1,
            "Found `%s`!=`1` %s columns for tag '%s'.",
            len(selected_cols_for_tag),
            selected_type,
            tag,
        )
        return selected_cols_for_tag[0]


# #############################################################################


# TODO(gp): This is probably more general than here. Probably we want to trim
#  the data also inside the pipeline.
def _trim_df_trading_hours(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove data outside trading hours.
    """
    df_time = df.index.time
    # TODO(gp): We should extend this to handle the overnight return.
    mask = (df_time >= datetime.time(9, 30)) & (df_time <= datetime.time(16, 0))
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug(mask.sum() / len(mask))
    hdbg.dassert_eq(len(df[~mask].dropna()), 0)
    return df[mask]
