"""
Import as:

import defi.dao_etf.tests.dao_etf_test as ddetdette
"""
# TODO(Juraj): brownie module not available in the current container version.
if False:
    from brownie import DaoETF, accounts


    def test_flow():
        """
        Test the main user flow that produces no errors.
        """
        owner = accounts[0]
        user = accounts[1]
        # Deploy the contract.
        dao_etf = DaoETF.deploy("Sorrentum Token", "SORR", {"from": owner})
        # Check the start balances.
        assert owner.balance() == 1000000000000000000000
        assert dao_etf.balance() == 0
        assert user.balance() == 1000000000000000000000
        # Invest to dao from the user balance.
        dao_etf.invest({"from": user, "value": 30000000000000000000})
        # Check whether the Dao ETH balance increased and user ETH balance decreased.
        assert dao_etf.balance() == 30000000000000000000
        assert user.balance() == 970000000000000000000
        # Check SURR token balance for the user, ETH:token proportion is 1:1.
        assert dao_etf.getUserTokenBalance(user) == 30000000000000000000
        # Test redeem.
        dao_etf.redeem(20000000000000000000, {"from": user})
        # Check whether the Dao ETH balance decreased and user ETH balance increased.
        assert dao_etf.balance() == 10000000000000000000
        assert user.balance() == 990000000000000000000
        # Check whether user has a proper amount of SURR tokens left.
        assert dao_etf.getUserTokenBalance(user) == 10000000000000000000
        # Withdraw ETH to the owner address.
        dao_etf.withdraw(10000000000000000000, {"from": owner})
        assert owner.balance() == 1010000000000000000000
        assert dao_etf.balance() == 0
