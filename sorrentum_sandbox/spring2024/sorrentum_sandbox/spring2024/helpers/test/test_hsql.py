import helpers.hsql as hsql
import helpers.hunit_test as hunitest


class TestCreateInOperator(hunitest.TestCase):
    def test_create_in_operator1(self) -> None:
        """
        Test creating IN operator for more than one value.
        """
        values = ["binance", "ftx"]
        column = "exchange_id"
        actual = hsql.create_in_operator(values, column)
        expected = "exchange_id IN ('binance','ftx')"
        self.assertEqual(actual, expected)

    def test_create_in_operator2(self) -> None:
        """
        Test creating IN operator for one value.
        """
        values = ["ftx"]
        column = "exchange_id"
        actual = hsql.create_in_operator(values, column)
        expected = "exchange_id IN ('ftx')"
        self.assertEqual(actual, expected)
