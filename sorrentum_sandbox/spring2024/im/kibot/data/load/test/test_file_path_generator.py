import helpers.hunit_test as hunitest
import im.common.data.types as imcodatyp
import im.kibot.data.config as imkidacon
import im.kibot.data.load.kibot_file_path_generator as imkdlkfpge


class TestFilePathGenerator(hunitest.TestCase):
    def test1(self) -> None:
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.Futures,
            contract_type=imcodatyp.ContractType.Continuous,
            frequency=imcodatyp.Frequency.Daily,
            ext=imcodatyp.Extension.CSV,
        )
        expected_file_path = "all_futures_continuous_contracts_daily/TEST.csv.gz"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def test2(self) -> None:
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.Futures,
            contract_type=imcodatyp.ContractType.Continuous,
            frequency=imcodatyp.Frequency.Daily,
            ext=imcodatyp.Extension.Parquet,
        )
        expected_file_path = "pq/all_futures_continuous_contracts_daily/TEST.pq"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def test3(self) -> None:
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.Futures,
            contract_type=imcodatyp.ContractType.Expiry,
            frequency=imcodatyp.Frequency.Daily,
            ext=imcodatyp.Extension.Parquet,
        )
        expected_file_path = "pq/all_futures_contracts_daily/TEST.pq"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def test4(self) -> None:
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.Futures,
            contract_type=imcodatyp.ContractType.Expiry,
            frequency=imcodatyp.Frequency.Minutely,
            ext=imcodatyp.Extension.Parquet,
        )
        expected_file_path = "pq/all_futures_contracts_1min/TEST.pq"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def test5(self) -> None:
        """
        Test generating file name for stocks without unadjusted raises
        exception.
        """
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.Stocks,
            frequency=imcodatyp.Frequency.Minutely,
            ext=imcodatyp.Extension.Parquet,
        )
        expected_file_path = "pq/all_stocks_unadjusted_1min/TEST.pq"

        with self.assertRaises(AssertionError):
            self._assert_file_path(
                args=args, expected_file_path=expected_file_path
            )

    def test6(self) -> None:
        """
        Test generating file name for unadjusted stocks works.
        """
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.Stocks,
            unadjusted=True,
            frequency=imcodatyp.Frequency.Minutely,
            ext=imcodatyp.Extension.Parquet,
        )
        expected_file_path = "pq/all_stocks_unadjusted_1min/TEST.pq"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def test7(self) -> None:
        """
        Test generating file name for unadjusted etfs works.
        """
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.ETFs,
            unadjusted=True,
            frequency=imcodatyp.Frequency.Minutely,
            ext=imcodatyp.Extension.Parquet,
        )
        expected_file_path = "pq/all_etfs_unadjusted_1min/TEST.pq"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def test8(self) -> None:
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.Futures,
            contract_type=imcodatyp.ContractType.Continuous,
            frequency=imcodatyp.Frequency.Tick,
            ext=imcodatyp.Extension.CSV,
        )
        expected_file_path = "all_futures_continuous_contracts_tick/TEST.csv.gz"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def test9(self) -> None:
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.Forex,
            frequency=imcodatyp.Frequency.Minutely,
            ext=imcodatyp.Extension.CSV,
        )
        expected_file_path = "all_forex_pairs_1min/TEST.csv.gz"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def test10(self) -> None:
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.Forex,
            frequency=imcodatyp.Frequency.Daily,
            ext=imcodatyp.Extension.CSV,
        )
        expected_file_path = "all_forex_pairs_daily/TEST.csv.gz"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def test11(self) -> None:
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.Stocks,
            unadjusted=False,
            frequency=imcodatyp.Frequency.Minutely,
            ext=imcodatyp.Extension.CSV,
        )
        expected_file_path = "all_stocks_1min/TEST.csv.gz"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def test12(self) -> None:
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.ETFs,
            unadjusted=False,
            frequency=imcodatyp.Frequency.Minutely,
            ext=imcodatyp.Extension.CSV,
        )
        expected_file_path = "all_etfs_1min/TEST.csv.gz"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def test13(self) -> None:
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.SP500,
            unadjusted=False,
            frequency=imcodatyp.Frequency.Tick,
            ext=imcodatyp.Extension.CSV,
        )
        expected_file_path = "sp_500_tick/TEST.csv.gz"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def test14(self) -> None:
        args = dict(
            symbol="TEST",
            aws_profile="ck",
            asset_class=imcodatyp.AssetClass.SP500,
            unadjusted=True,
            frequency=imcodatyp.Frequency.Tick,
            ext=imcodatyp.Extension.CSV,
        )
        expected_file_path = "sp_500_unadjusted_tick/TEST.csv.gz"
        self._assert_file_path(args=args, expected_file_path=expected_file_path)

    def _assert_file_path(self, args: dict, expected_file_path: str) -> None:
        generator = imkdlkfpge.KibotFilePathGenerator()
        actual = generator.generate_file_path(**args)
        s3_prefix = imkidacon.get_s3_prefix("ck")
        expected = f"{s3_prefix}/{expected_file_path}"
        self.assertEqual(actual, expected)
