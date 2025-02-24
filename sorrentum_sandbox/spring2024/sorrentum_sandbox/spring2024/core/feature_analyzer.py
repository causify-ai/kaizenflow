"""
Import as:

import core.feature_analyzer as cfeaanal
"""

import collections
import logging
from typing import Dict, List, Tuple, Union

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import statsmodels.api as sm

import helpers.hdbg as hdbg
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


# TODO(gp): Likely obsolete.


def _analyze_feature(
    df: pd.DataFrame,
    y_var: str,
    x_var: str,
    use_intercept: bool,
    nan_mode: str,
    x_shift: int,
    report_stats: bool,
) -> collections.OrderedDict:
    _LOG.debug("df=\n%s", df.head(3))
    _LOG.debug(
        "y_var=%s, x_var=%s, use_intercept=%s, nan_mode=%s, x_shift=%s",
        y_var,
        x_var,
        use_intercept,
        nan_mode,
        x_shift,
    )
    hdbg.dassert_isinstance(y_var, str)
    hdbg.dassert_isinstance(x_var, str)
    #
    res = collections.OrderedDict()
    res["y_var"] = y_var
    res["x_var"] = x_var
    df_tmp = df[[y_var, x_var]].copy()
    #
    res["x_shift"] = x_shift
    if x_shift != 0:
        df_tmp[x_var] = df_tmp[x_var].shift(x_shift)
    #
    if nan_mode == "drop":
        df_tmp.dropna(inplace=True)
    elif nan_mode == "fill_with_zeros":
        df_tmp.fillna(0.0, inplace=True)
    else:
        raise ValueError("Invalid nan_mode='%s'" % nan_mode)
    res["nan_mode"] = nan_mode
    #
    regr_x_vars = [x_var]
    if use_intercept:
        df_tmp = sm.add_constant(df_tmp)
        regr_x_vars.insert(0, "const")
    res["use_intercept"] = use_intercept
    # Fit.
    reg = sm.OLS(df_tmp[y_var], df_tmp[regr_x_vars])
    model = reg.fit()
    if use_intercept:
        hdbg.dassert_eq(len(model.params), 2)
        res["params_const"] = model.params[0]
        res["pvalues_const"] = model.pvalues[0]
        res["params_var"] = model.params[1]
        res["pvalues_var"] = model.pvalues[1]
    else:
        hdbg.dassert_eq(len(model.params), 1)
        res["params_var"] = model.params[0]
        res["pvalues_var"] = model.pvalues[0]
    res["nobs"] = model.nobs
    res["condition_number"] = model.condition_number
    res["rsquared"] = model.rsquared
    res["rsquared_adj"] = model.rsquared_adj
    # TODO(gp): Add pnl, correlation, hitrate.
    #
    if report_stats:
        txt = hprint.frame(
            "y_var=%s, x_var=%s, use_intercept=%s, nan_mode=%s, x_shift=%s"
            % (y_var, x_var, use_intercept, nan_mode, x_shift)
        )
        _LOG.info("\n%s", txt)
        _LOG.info("model.summary()=\n%s", model.summary())
        sns.regplot(x=df[x_var], y=df[y_var])
        plt.show()
    return res


def analyze_features(
    df: pd.DataFrame,
    y_var: str,
    x_vars: List[str],
    use_intercept: bool,
    nan_mode: str = "drop",
    x_shifts: Union[None, List[int]] = None,
    report_stats: bool = False,
) -> pd.DataFrame:
    if x_shifts is None:
        x_shifts = [0]
    res_df = []
    for x_var in x_vars:
        _LOG.debug("x_var=%s", x_var)
        for x_shift in x_shifts:
            _LOG.debug("x_shifts=%s", x_shift)
            res_tmp = _analyze_feature(
                df, y_var, x_var, use_intercept, nan_mode, x_shift, report_stats
            )
            res_df.append(res_tmp)
    return pd.DataFrame(res_df)


# #############################################################################


class Reporter:
    """
    Report results from `analyze_features()` in a heatmap with coefficient
    values and p-values.
    """

    def __init__(self, res_df: pd.DataFrame):
        self.res_df = res_df

    def plot(self) -> pd.DataFrame:
        # Reshape the results in terms of coeff values and pvalues.
        coeff_df = self.res_df[
            ["x_var", "x_shift", "params_var", "pvalues_var"]
        ].pivot(index="x_shift", columns="x_var", values="params_var")
        pvals_df = self.res_df[
            ["x_var", "x_shift", "params_var", "pvalues_var"]
        ].pivot(index="x_shift", columns="x_var", values="pvalues_var")
        min_val = coeff_df.min(axis=0).min()
        max_val = coeff_df.max(axis=0).max()
        # Df storing the results.
        coeff_df_tmp = coeff_df.copy()
        # Map from cell text in coeff_df_map to color.
        coeff_color_map = {}
        #
        for i in range(coeff_df_tmp.shape[0]):
            for j in range(coeff_df_tmp.shape[1]):
                coeff = coeff_df.iloc[i, j]
                _LOG.debug("i=%s j=%s -> coeff=%s", i, j, coeff)
                # Compute color.
                color = self._assign_color(coeff, min_val, max_val)
                # Present coeff and pval.
                coeff = "%.3f" % coeff
                pval = pvals_df.iloc[i, j]
                if pval < 0.001:
                    # 0.1%
                    coeff += " (***)"
                elif pval < 0.01:
                    # 1%
                    coeff += " (**)"
                elif pval < 0.05:
                    # 5%
                    coeff += " (*)"
                else:
                    # coeff = ""
                    pass
                coeff_df_tmp.iloc[i, j] = coeff
                coeff_color_map[coeff] = color
        # Style df by assigning colors.
        decorate_with_color = lambda val: self._decorate_with_color(
            val, coeff_color_map
        )
        coeff_df_tmp = coeff_df_tmp.style.applymap(decorate_with_color)
        return coeff_df_tmp

    @staticmethod
    def _interpolate(
        val: float, max_val: float, min_col: float, max_col: float
    ) -> int:
        """
        Interpolate intensity in [min_col, max_col] based on val in 0,
        max_val].

        :return: float value in [0, 1]
        """
        hdbg.dassert_lte(0, val)
        hdbg.dassert_lte(val, max_val)
        res = min_col + (val / max_val * (max_col - min_col))
        return int(res)

    @staticmethod
    def _interpolate_rgb(
        val: float,
        max_val: float,
        min_rgb: Tuple[int, int, int],
        max_rgb: Tuple[int, int, int],
    ) -> List[int]:
        """
        Interpolate val in [0, max_val] in terms of the rgb colors.

        [min_rgb, max_rgb] by interpolating the 3 color channels.
        :return: triple representing the interpolated color
        """
        res = []
        for min_, max_ in zip(min_rgb, max_rgb):
            res.append(Reporter._interpolate(val, max_val, min_, max_))
        return res

    @staticmethod
    def _assign_color(val: float, min_val: float, max_val: float) -> str:
        if val < 0:
            min_rgb = (255, 255, 255)
            max_rgb = (96, 96, 255)
            rgb = Reporter._interpolate_rgb(-val, -min_val, min_rgb, max_rgb)
        else:
            min_rgb = (255, 255, 255)
            max_rgb = (255, 96, 96)
            rgb = Reporter._interpolate_rgb(val, max_val, min_rgb, max_rgb)
        # E.g., color = '#FF0000'
        color = "#{:02x}{:02x}{:02x}".format(*rgb)
        _LOG.debug(
            "val=%s in [%s, %s] -> rgb=%s %s", val, min_val, max_val, rgb, color
        )
        return color

    @staticmethod
    def _decorate_with_color(txt: str, color_map: Dict[str, str]) -> str:
        hdbg.dassert_in(txt, color_map)
        color = color_map[txt]
        return "background-color: %s" % color


# TODO(gp): Add unit test.
# print(color_negative_red(val=2, min_val=-2, max_val=2))
# print(color_negative_red(val=-2, min_val=-2, max_val=2))
# print(color_negative_red(val=0.001, min_val=-2, max_val=2))
