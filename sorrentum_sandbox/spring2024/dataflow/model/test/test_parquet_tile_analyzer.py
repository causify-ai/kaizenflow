import logging

import pandas as pd

import core.finance_data_example as cfidaexa
import dataflow.model.parquet_tile_analyzer as dtfmpatian
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class TestParquetTileAnalyzer(hunitest.TestCase):
    @staticmethod
    def generate_tiles(dir_name) -> None:
        # Generate fake dataflow-style data.
        df = cfidaexa.get_forecast_dataframe(
            pd.Timestamp("2022-01-20 09:30:00", tz="America/New_York"),
            pd.Timestamp("2022-02-10 16:00:00", tz="America/New_York"),
            [100, 200, 300, 400],
            bar_duration="30T",
        )
        # Preprocess before converting to parquet.
        df = df.stack()
        df.index.names = ["end_ts", "asset_id"]
        df = df.reset_index(level=1)
        df["year"] = df.index.year
        df["month"] = df.index.month
        # Write the parquet tiles.
        hparque.to_partitioned_parquet(
            df, ["asset_id", "year", "month"], dst_dir=dir_name
        )

    def test_collate_parquet_tile_metadata1(self) -> None:
        dir_name = self.get_scratch_space()
        self.generate_tiles(dir_name)
        pta = dtfmpatian.ParquetTileAnalyzer()
        metadata = pta.collate_parquet_tile_metadata(dir_name)
        # TODO(Grisha): see CmTask3227 "Parquet metadata is different
        # on the dev server and on GH server".
        metadata = metadata["file_size"]
        actual = hpandas.df_to_str(metadata, num_rows=None, precision=3)
        expected = r"""
                    file_size
asset_id year month
100      2022 1        9.9 KB
              2        9.0 KB
200      2022 1        9.9 KB
              2        9.0 KB
300      2022 1        9.9 KB
              2        9.0 KB
400      2022 1        9.9 KB
              2        9.0 KB
        """
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_compute_metadata_stats_by_asset_id(self) -> None:
        dir_name = self.get_scratch_space()
        self.generate_tiles(dir_name)
        pta = dtfmpatian.ParquetTileAnalyzer()
        metadata = pta.collate_parquet_tile_metadata(dir_name)
        metadata_stats = pta.compute_metadata_stats_by_asset_id(metadata)
        actual = hpandas.df_to_str(metadata_stats, num_rows=None, precision=3)
        expected = r"""
        n_years n_unique_months n_files    size
asset_id
100     1       2               2       18.8 KB
200     1       2               2       18.8 KB
300     1       2               2       18.8 KB
400     1       2               2       18.8 KB"""
        self.assert_equal(actual, expected, fuzzy_match=True)

    def test_compute_universe_size_by_time(self) -> None:
        dir_name = self.get_scratch_space()
        self.generate_tiles(dir_name)
        pta = dtfmpatian.ParquetTileAnalyzer()
        metadata = pta.collate_parquet_tile_metadata(dir_name)
        metadata_stats = pta.compute_universe_size_by_time(metadata)
        actual = hpandas.df_to_str(metadata_stats, num_rows=None, precision=3)
        expected = r"""
            n_asset_ids     size
year month
2022 1                4  39.5 KB
     2                4  35.8 KB"""
        self.assert_equal(actual, expected, fuzzy_match=True)
