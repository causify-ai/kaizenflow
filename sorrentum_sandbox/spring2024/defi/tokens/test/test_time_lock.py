# TODO(Juraj): brownie module not available in the current container version.
if False:
    import brownie
    import pytest


    @pytest.fixture(scope="module")
    def time_lock(mock_token, TokenTimelock, accounts):
        """
        Deploy the TokenTimeLock Contract.
        """
        return TokenTimelock.deploy(
            mock_token.address, {"from": accounts[0], "gas_price": "60 gwei"}
        )


    @pytest.fixture(scope="module")
    def mock_token(MockERC20, accounts):
        """
        Deploy the MockERC20 contract.
        """
        return MockERC20.deploy(
            "Mock Token",
            "MCK",
            1000,
            10000,
            {"from": accounts[1], "gas_price": "60 gwei"},
        )


    @pytest.fixture(autouse=True)
    def shared_setup(fn_isolation):
        """
        Creates the isolation environment.
        """
        pass


    def test_addParticipant_requireAmount(time_lock, accounts):
        """
        Check whether the participant amount equals to 0 before being added.
        """
        participant = accounts[2]
        amount = 10000
        release_TimeStamp = 1677064547
        time_lock.addParticipant(
            participant,
            amount,
            release_TimeStamp,
            {"from": accounts[0], "gas_price": "60 gwei"},
        )
        with brownie.reverts():
            time_lock.addParticipant(
                participant,
                amount,
                release_TimeStamp,
                {"from": accounts[0], "gas_price": "60 gwei"},
            )


    def test_addParticipant(time_lock, accounts):
        """
        Checks whether the participant has been added.
        """
        participant = accounts[2]
        amount = 10000
        release_TimeStamp = 1677064547
        time_lock.addParticipant(
            participant,
            amount,
            release_TimeStamp,
            {"from": accounts[0], "gas_price": "60 gwei"},
        )
        assert (
            time_lock.getTokensAmountLocked(participant, {"from": participant})
            == amount
        )


    def test_addAmount_requireAmount(time_lock, accounts):
        """
        Checks participants amount != 0.
        """
        with brownie.reverts():
            time_lock.addAmount(
                accounts[1], 1000, {"from": accounts[0], "gas_price": "60 gwei"}
            )


    def test_addAmount(time_lock, accounts):
        """
        Checks the flow of addAmount function.
        """
        participant = accounts[2]
        amount = 10000
        release_TimeStamp = 1677064547
        time_lock.addParticipant(
            participant,
            amount,
            release_TimeStamp,
            {"from": accounts[0], "gas_price": "60 gwei"},
        )
        new_amount = 1000
        final_amount = amount + new_amount
        time_lock.addAmount(
            accounts[2], new_amount, {"from": accounts[0], "gas_price": "60 gwei"}
        )
        assert (
            time_lock.getTokensAmountLocked(participant, {"from": participant})
            == final_amount
        )


    def test_getReleaseTimestamp(time_lock, accounts):
        """
        Checks the flow of getReleaseTimestamp function.
        """
        with brownie.reverts():
            time_lock.getReleaseTimestamp(accounts[1], {"from": accounts[1]})


    def test_releaseTokens_releaseTimestamp(time_lock, accounts, mock_token):
        """
        Checks release_timestamp < block_time while releasing the tokens.
        """
        participant = accounts[2]
        amount = 3 * 10**18
        release_TimeStamp = 1677064547
        time_lock.addParticipant(
            participant,
            amount,
            release_TimeStamp,
            {"from": accounts[0], "gas_price": "60 gwei"},
        )

        with brownie.reverts():
            time_lock.releaseTokens({"from": accounts[1], "gas_price": "60 gwei"})


    def test_releaseTokens(time_lock, accounts, mock_token):
        """
        Checks the flow of releaseTokens function.
        """
        participant = accounts[2]
        amount = 3 * 10**18
        release_TimeStamp = 1677064547
        time_lock.addParticipant(
            participant,
            amount,
            release_TimeStamp,
            {"from": accounts[0], "gas_price": "60 gwei"},
        )
        brownie.chain.sleep(release_TimeStamp - brownie.chain.time() + 1)
        mock_token.transfer(
            time_lock.address, amount, {"from": accounts[1], "gas_price": "60 gwei"}
        )
        time_lock.releaseTokens({"from": accounts[2], "gas_price": "60 gwei"})
        assert mock_token.balanceOf(accounts[2]) == amount


    def test_withDrawTokens_ownerCheck(time_lock, accounts):
        """
        Checks whether withdrawTokens function is called by Owner.
        """
        with brownie.reverts():
            time_lock.withdrawTokens(5, {"from": accounts[2], "gas_price": "60 gwei"})


    def test_withDrawTokens(time_lock, accounts, mock_token):
        """
        Checks the flow of withdrawTokens function.
        """
        amount = 3 * 10**18
        mock_token.transfer(
            time_lock.address, amount, {"from": accounts[1], "gas_price": "60 gwei"}
        )
        time_lock.withdrawTokens(
            amount, {"from": accounts[0], "gas_price": "60 gwei"}
        )
        assert mock_token.balanceOf(accounts[0]) == amount


    def test_contractBalance(time_lock, accounts, mock_token):
        """
        Checks the flow of getContractBalance function.
        """
        amount = 3 * 10**18
        mock_token.transfer(
            time_lock.address, amount, {"from": accounts[1], "gas_price": "60 gwei"}
        )
        assert time_lock.getContractBalance({"from": accounts[0]}) == amount
