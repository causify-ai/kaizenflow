import logging
import unittest

import pandas as pd

import core.plotting.correlation as cplocorr

_LOG = logging.getLogger(__name__)


class Test_select_series_to_remove(unittest.TestCase):
    def test_select_series_to_remove1(self) -> None:
        """
        Test correct output of df correlation with threashold = 0.7
        """
        data = {
            "A": [45, 37, 42, 35, 39],
            "B": [38, 31, 26, 28, 33],
            "C": [10, 15, 17, 21, 12],
            "D": [9, 13, 16, 15, 12],
            "E": [9, 9, 7, 5, 10],
        }

        df = pd.DataFrame(data, columns=["A", "B", "C", "D", "E"])
        expected = ["C"]
        actual = cplocorr.select_series_to_keep(df.corr(), 0.7)
        self.assertListEqual(actual, expected)

    def test_select_series_to_remove2(self) -> None:
        """
        Test correct output of df correlation with threashold = 0.5
        """
        data = {
            "A": [45, 37, 42, 35, 39],
            "B": [38, 31, 26, 28, 33],
            "C": [10, 15, 17, 21, 12],
            "D": [9, 13, 16, 15, 12],
            "E": [9, 9, 7, 5, 10],
        }

        df = pd.DataFrame(data, columns=["A", "B", "C", "D", "E"])
        expected = ["B"]
        actual = cplocorr.select_series_to_keep(df.corr(), 0.5)
        self.assertListEqual(actual, expected)

    def test_select_series_to_remove3(self) -> None:
        """
        Test correct output of df correlation with threashold = 0.3
        """
        data = {
            "A": [45, 37, 42, 35, 39],
            "B": [38, 31, 26, 28, 33],
            "C": [10, 15, 17, 21, 12],
            "D": [9, 13, 16, 15, 12],
            "E": [9, 9, 7, 5, 10],
        }

        df = pd.DataFrame(data, columns=["A", "B", "C", "D", "E"])
        expected = ["A"]
        actual = cplocorr.select_series_to_keep(df.corr(), 0.3)
        self.assertListEqual(actual, expected)

    def test_select_series_to_remove4(self) -> None:
        """
        Test correct output of df correlation with threashold = 0.7
        """
        data = {
            "A": [1, 4, 4, 4, 5, 9],
            "B": [2, 6, 3, 4, 5, 10],
            "C": [3, 6, 4, 4, 5, 10],
            "D": [4, 25, 19, 14, 15, 10],
            "E": [5, 27, 16, 16, 14, 11],
            "F": [1, 8, 4, 4, 5, 10],
            "G": [15, 24, 32, 56, 23, 25],
        }

        df = pd.DataFrame(data, columns=["A", "B", "C", "D", "E", "F", "G"])
        expected = ["A", "D", "G"]
        actual = cplocorr.select_series_to_keep(df.corr(), 0.7)
        self.assertListEqual(actual, expected)

    def test_select_series_to_remove5(self) -> None:
        """
        Test correct output of df correlation with threashold = 0.5
        """
        data = {
            "A": [1, 4, 4, 4, 5, 9],
            "B": [2, 6, 3, 4, 5, 10],
            "C": [3, 6, 4, 4, 5, 10],
            "D": [4, 25, 19, 14, 15, 10],
            "E": [5, 27, 16, 16, 14, 11],
            "F": [1, 8, 4, 4, 5, 10],
            "G": [15, 24, 32, 56, 23, 25],
        }

        df = pd.DataFrame(data, columns=["A", "B", "C", "D", "E", "F", "G"])
        expected = ["F", "G"]
        actual = cplocorr.select_series_to_keep(df.corr(), 0.3)
        self.assertListEqual(actual, expected)
