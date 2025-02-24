import helpers.hunit_test as hunitest
import im.kibot.metadata.load.expiry_contract_mapper as imkmlecoma


class TestExpiryContractMapper(hunitest.TestCase):
    def test_parse_expiry_contract1(self) -> None:
        """
        Valid input returns valid output.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = "TTH10"
        exp = ("TT", "H", "10")
        act = cls.parse_expiry_contract(inp)
        self.assertEqual(exp, act)

    def test_parse_expiry_contract2(self) -> None:
        """
        Valid input with 1 letter contract returns valid input.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = "TU10"
        exp = ("T", "U", "10")
        act = cls.parse_expiry_contract(inp)
        self.assertEqual(exp, act)

    def test_parse_expiry_contract3(self) -> None:
        """
        Incorrect input returns an error.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = "TTH1"
        with self.assertRaises(AssertionError):
            cls.parse_expiry_contract(inp)

    def test_compare_expiry_contract1(self) -> None:
        """
        Valid input with x > y based on months returns valid output.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = ("TUG10", "TUF10")
        exp = 1
        act = cls.compare_expiry_contract(*inp)
        self.assertEqual(exp, act)

    def test_compare_expiry_contract2(self) -> None:
        """
        Valid input with x < y based on months returns valid output.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = ("TUF10", "TUG10")
        exp = -1
        act = cls.compare_expiry_contract(*inp)
        self.assertEqual(exp, act)

    def test_compare_expiry_contract3(self) -> None:
        """
        Valid input with x == y returns valid output.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = ("TUF10", "TUF10")
        exp = 0
        act = cls.compare_expiry_contract(*inp)
        self.assertEqual(exp, act)

    def test_compare_expiry_contract4(self) -> None:
        """
        Valid input with x > y based on months returns valid output.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = ("TUF11", "TUF10")
        exp = 1
        act = cls.compare_expiry_contract(*inp)
        self.assertEqual(exp, act)

    def test_compare_expiry_contract5(self) -> None:
        """
        Valid input with x < y based on months returns valid output.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = ("TUF10", "TUF11")
        exp = -1
        act = cls.compare_expiry_contract(*inp)
        self.assertEqual(exp, act)

    def test_compare_expiry_contract6(self) -> None:
        """
        Invalid input raises an error.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = ("TU10", "TTU10")
        with self.assertRaises(AssertionError):
            cls.compare_expiry_contract(*inp)

    def test_compare_expiry_contract7(self) -> None:
        """
        Empty input raises an error.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = ("", "")
        with self.assertRaises(AssertionError):
            cls.compare_expiry_contract(*inp)

    def test_sort_expiry_contract1(self) -> None:
        """
        Valid input with differing months returns valid output.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = ["TTZ10", "TTV10", "TTX10", "TTN10", "TTQ10"]
        exp = ["TTN10", "TTQ10", "TTV10", "TTX10", "TTZ10"]
        act = cls.sort_expiry_contract(inp)
        self.assertEqual(exp, act)

    def test_sort_expiry_contract2(self) -> None:
        """
        Valid input with differing years returns valid output.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = ["TTF15", "TTF13", "TTF14", "TTF17", "TTF11"]
        exp = ["TTF11", "TTF13", "TTF14", "TTF15", "TTF17"]
        act = cls.sort_expiry_contract(inp)
        self.assertEqual(exp, act)

    def test_sort_expiry_contract3(self) -> None:
        """
        Valid input with differing months & years returns valid output.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = ["TTK15", "TTG13", "TTJ14", "TTK17", "TTF11"]
        exp = ["TTF11", "TTG13", "TTJ14", "TTK15", "TTK17"]
        act = cls.sort_expiry_contract(inp)
        self.assertEqual(exp, act)

    def test_sort_expiry_contract4(self) -> None:
        """
        Valid input with duplicate dates returns valid output.
        """
        cls = imkmlecoma.ExpiryContractMapper()
        inp = ["TTK15", "TTG13", "TTG15", "TTG17", "TTF11"]
        exp = ["TTF11", "TTG13", "TTG15", "TTK15", "TTG17"]
        act = cls.sort_expiry_contract(inp)
        self.assertEqual(exp, act)
