# TODO(Juraj): brownie module not available in the current container version.
if False:
    import pytest
    from brownie import (
        Contract,
        DaoCross,
        MockERC20,
        MockV3Aggregator,
        accounts,
        reverts,
    )

    # Deploy the MockV3Aggregator
    @pytest.fixture(scope="module")
    def price_oracle():
        decimals = 18
        initial_price = 100000000000  # This value should be scaled to the appropriate number of decimals
        mock_v3_aggregator = accounts[0].deploy(
            MockV3Aggregator, decimals, initial_price
        )
        yield mock_v3_aggregator


    @pytest.fixture
    def base_token(accounts):
        return accounts[0].deploy(MockERC20, "BaseToken", "BT")


    @pytest.fixture
    def daocross(price_oracle, base_token):
        return accounts[0].deploy(
            DaoCross,
            base_token.address,
            300,
            5,
            1,
            price_oracle.address,
        )


    def test_buyOrder_baseToken_address(daocross, base_token):
        """
        Check if the error is asserted when the token to buy is not equal
        to the base token of the contract.
        """
        baseToken = "0x1234567890123456789012345678901234567890"
        quantity = 5 * 10**18
        limitPrice = 100000000000
        depositAddress = accounts[1]
        with reverts():
            daocross.buyOrder(
                baseToken,
                quantity,
                limitPrice,
                depositAddress,
                {
                    "from": accounts[1],
                    "value": limitPrice * 5,
                    "gas_price": "60 gwei",
                },
            )


    def test_buyOrder_passedEther(daocross, base_token):
        """
        Check whether the amount of ETH transferred with the function call meet or exceed the total amount user wants to spend.
        """
        quantity = 5 * 10**18
        limitPrice = 100000000000
        depositAddress = accounts[1]
        with reverts():
            daocross.buyOrder(
                base_token.address,
                quantity,
                limitPrice,
                depositAddress,
                {
                    "from": accounts[1],
                    "value": 100000000000 * 4,
                    "gas_price": "60 gwei",
                },
            )


    def test_buyOrder_orderArray(daocross, base_token):
        """
        Check if the length of order array is increased after creating the buy orders.

        Buy 5 tokens for 100000000000 WEI.
        Buy 2.5 tokens for 100000000000 WEI.
        """
        limitPrice = 100000000000
        daocross.buyOrder(
            base_token.address,
            5 * 10**18,
            limitPrice,
            accounts[1],
            {"from": accounts[1], "value": limitPrice * 5, "gas_price": "60 gwei"},
        )
        daocross.buyOrder(
            base_token.address,
            2.5 * 10**18,
            limitPrice,
            accounts[2],
            {"from": accounts[2], "value": limitPrice * 2.5, "gas_price": "60 gwei"},
        )
        assert daocross.orders(0)[0] == 0
        assert daocross.orders(1)[0] == 1


    def test_buyOrder_eventEmitted(daocross, base_token):
        """
        Check whether the newBuyOrder event was emitted or not.
        """
        quantity = 5 * 10**18
        limitPrice = 100000000000
        depositAddress = accounts[1]
        ethAddress = "0x0000000000000000000000000000000000000000"
        tx = daocross.buyOrder(
            base_token.address,
            quantity,
            limitPrice,
            depositAddress,
            {"from": accounts[1], "value": 100000000000 * 5, "gas_price": "60 gwei"},
        )
        assert len(tx.events) == 1
        assert tx.events["newBuyOrder"].values() == [
            base_token.address,
            ethAddress,
            quantity,
            limitPrice,
            depositAddress,
        ]


    def test_sellOrder_baseToken_address(daocross, base_token):
        """
        Check if the error is asserted when the token to sell is not equal
        to the base token of the contract.
        """
        baseToken = "0x1234567890123456789012345678901234567890"
        quantity = 5 * 10**18
        limitPrice = 100000000000
        depositAddress = accounts[1]
        with reverts():
            daocross.sellOrder(
                baseToken,
                quantity,
                limitPrice,
                depositAddress,
                {"from": accounts[1], "gas_price": "60 gwei"},
            )


    def test_sellOrder_allowance(daocross, base_token):
        """
        Check if the allowance by the token seller is greater than or equal to the quantity.
        """
        base_token.transfer(
            accounts[5], 5 * 10**18, {"from": accounts[0], "gas_price": "60 gwei"}
        )
        base_token.approve(
            daocross, 5 * 10**18, {"from": accounts[5], "gas_price": "60 gwei"}
        )
        quantity = 6 * 10**18
        limitPrice = 100000000000
        depositAddress = accounts[5]
        with reverts():
            daocross.sellOrder(
                base_token.address,
                quantity,
                limitPrice,
                depositAddress,
                {"from": accounts[5], "gas_price": "60 gwei"},
            )


    def test_sellOrder_checkBalance(daocross, base_token):
        """
        Check if the contract receives the correct amount of ERC-20 tokens from submitted sell orders.
        """
        base_token.transfer(
            accounts[5], 5 * 10**18, {"from": accounts[0], "gas_price": "60 gwei"}
        )
        base_token.approve(
            daocross, 5 * 10**18, {"from": accounts[5], "gas_price": "60 gwei"}
        )
        quantity = 5 * 10**18
        limitPrice = 100000000000
        depositAddress = accounts[5]
        daocross.sellOrder(
            base_token.address,
            quantity,
            limitPrice,
            depositAddress,
            {"from": accounts[5], "gas_price": "60 gwei"},
        )
        assert base_token.balanceOf(daocross.address) == quantity


    def test_sellOrder_orderArray(daocross, base_token):
        """
        Check if the length of order array is increased after creating the sell orders.

        Sell 5 tokens.
        Sell 2.5 tokens.
        """
        base_token.transfer(
            accounts[5], 5 * 10**18, {"from": accounts[0], "gas_price": "60 gwei"}
        )
        base_token.approve(
            daocross, 5 * 10**18, {"from": accounts[5], "gas_price": "60 gwei"}
        )
        base_token.transfer(
            accounts[6], 5 * 10**18, {"from": accounts[0], "gas_price": "60 gwei"}
        )
        base_token.approve(
            daocross, 5 * 10**18, {"from": accounts[6], "gas_price": "60 gwei"}
        )
        daocross.sellOrder(
            base_token.address,
            5 * 10**18,
            100000000000,
            accounts[5],
            {"from": accounts[5], "gas_price": "60 gwei"},
        )
        daocross.sellOrder(
            base_token.address,
            2.5 * 10**18,
            100000000000,
            accounts[6],
            {"from": accounts[6], "gas_price": "60 gwei"},
        )
        assert daocross.orders(0)[0] == 0
        assert daocross.orders(1)[0] == 1


    def test_sellOrder_eventEmitted(daocross, base_token):
        """
        Check whether the newSellOrder event was emitted or not.
        """
        base_token.transfer(
            accounts[5], 5 * 10**18, {"from": accounts[0], "gas_price": "60 gwei"}
        )
        base_token.approve(
            daocross, 5 * 10**18, {"from": accounts[5], "gas_price": "60 gwei"}
        )
        quantity = 5 * 10**18
        limitPrice = 100000000000
        depositAddress = accounts[5]
        ethAddress = "0x0000000000000000000000000000000000000000"
        tx = daocross.sellOrder(
            base_token.address,
            5 * 10**18,
            100000000000,
            accounts[5],
            {"from": accounts[5], "gas_price": "60 gwei"},
        )
        assert tx.events["newSellOrder"].values() == [
            base_token.address,
            ethAddress,
            quantity,
            limitPrice,
            depositAddress,
        ]


    def test_getChainlinkFeedPrice(daocross):
        """
        Check whether the MockV3Aggregator gets the latest price.
        """
        assert daocross.getChainlinkFeedPrice() == 100000000000


    def test_onSwapTime_similarQuantity(daocross, base_token):
        """
        Check whether the token transfers occurs with single order of same quantity.
        Also check whether the eraseOrders() function deletes the orders from the array.
        """
        base_token.transfer(
            accounts[5], 5 * 10**18, {"from": accounts[0], "gas_price": "60 gwei"}
        )
        base_token.approve(
            daocross, 5 * 10**18, {"from": accounts[5], "gas_price": "60 gwei"}
        )
        daocross.buyOrder(
            base_token.address,
            5 * 10**18,
            100000000000,
            accounts[1],
            {"from": accounts[1], "value": 100000000000 * 5, "gas_price": "60 gwei"},
        )
        daocross.sellOrder(
            base_token.address,
            5 * 10**18,
            100000000000,
            accounts[5],
            {"from": accounts[5], "gas_price": "60 gwei"},
        )
        daocross.onSwapTime({"from": accounts[0], "gas_price": "60 gwei"})
        # Check if buyer received the desired amount of tokens.
        assert base_token.balanceOf(accounts[1]) == 5 * 10**18
        # Check if the Orders array is deleted after the swapping.
        with reverts():
            daocross.orders(0)[0] == 0


    def test_onSwapTime_sellOrder_with_greater_than_limitPrice(daocross, base_token):
        """
        Check if the tokens are returned to the user if the desired sell price is greater than the actual token price.
        """
        base_token.transfer(
            accounts[5], 5 * 10**18, {"from": accounts[0], "gas_price": "60 gwei"}
        )
        base_token.approve(
            daocross, 5 * 10**18, {"from": accounts[5], "gas_price": "60 gwei"}
        )
        daocross.buyOrder(
            base_token.address,
            5 * 10**18,
            100000000000,
            accounts[1],
            {"from": accounts[1], "value": 100000000000 * 5, "gas_price": "60 gwei"},
        )
        daocross.sellOrder(
            base_token.address,
            5 * 10**18,
            200000000000,
            accounts[5],
            {"from": accounts[5], "gas_price": "60 gwei"},
        )
        daocross.onSwapTime({"from": accounts[0], "gas_price": "60 gwei"})
        assert base_token.balanceOf(accounts[5]) == 5 * 10**18


    def test_onSwapTime_buyOrder_with_less_than_limitPrice(daocross, base_token):
        """
        Check if the ETH are returned to the user if the desired buy price is less than the actual token price.
        """
        initialBalance = accounts[6].balance()
        base_token.transfer(
            accounts[5], 5 * 10**18, {"from": accounts[0], "gas_price": "60 gwei"}
        )
        base_token.approve(
            daocross, 5 * 10**18, {"from": accounts[5], "gas_price": "60 gwei"}
        )
        daocross.buyOrder(
            base_token.address,
            5 * 10**18,
            100000000,
            accounts[6],
            {"from": accounts[6], "value": 100000000 * 5, "gas_price": "60 gwei"},
        )
        daocross.sellOrder(
            base_token.address,
            5 * 10**18,
            200000000000,
            accounts[5],
            {"from": accounts[5], "gas_price": "60 gwei"},
        )
        daocross.onSwapTime({"from": accounts[0], "gas_price": "60 gwei"})
        assert base_token.balanceOf(accounts[5]) == 5 * 10**18


    def test_onSwapTime_remainingHeap_moreBuying(daocross, base_token):
        """
        Check if after the token transfers, the remaining tokens are transfered to the owner of the tokens.

        Buying 11.5 tokens and selling 10 tokens.
        """
        # Add some sell orders, overall sell 10 tokens.
        n_tokens = [2, 5, 3]
        account_ind = [4, 5, 6]
        for n, ind in zip(n_tokens, account_ind):
            # Transfer the token to the users that will participate sell order.
            base_token.transfer(
                accounts[ind],
                n * 10**18,
                {"from": accounts[0], "gas_price": "60 gwei"},
            )
            # Approve the transfers for the contract.
            base_token.approve(
                daocross,
                n * 10**18,
                {"from": accounts[ind], "gas_price": "60 gwei"},
            )
            # Submit sell order.
            daocross.sellOrder(
                base_token.address,
                n * 10**18,
                100000000000,
                accounts[ind],
                {"from": accounts[ind], "gas_price": "60 gwei"},
            )
        # Buy 5 tokens for 100000000000 WEI.
        daocross.buyOrder(
            base_token.address,
            5 * 10**18,
            100000000000,
            accounts[1],
            {"from": accounts[1], "gas_price": "60 gwei", "value": 100000000000 * 5},
        )
        # Balance after placing the order.
        initialBalance = accounts[1].balance()
        # Buy 2.5 tokens for 100000000000 WEI.
        daocross.buyOrder(
            base_token.address,
            2.5 * 10**18,
            100000000000,
            accounts[2],
            {
                "from": accounts[2],
                "gas_price": "60 gwei",
                "value": 100000000000 * 2.5,
            },
        )
        # Buy 4 tokens for 100000000000 WEI.
        daocross.buyOrder(
            base_token.address,
            4 * 10**18,
            100000000000,
            accounts[3],
            {"from": accounts[3], "gas_price": "60 gwei", "value": 100000000000 * 4},
        )
        daocross.onSwapTime({"from": accounts[0], "gas_price": "60 gwei"})
        # Check that user that wanted to buy 5 tokens, gets only 3.5 tokens.
        assert base_token.balanceOf(accounts[1]) == 3.5 * 10**18
        # Check that buyer got their extra money for unbought 1.5 token back.
        assert accounts[1].balance() == initialBalance + 100000000000 * 1.5
        # Check that user that wanted to buy 2.5 tokens gets 2.5 tokens.
        assert base_token.balanceOf(accounts[2]) == 2.5 * 10**18
        # Check that user that wanted to buy 4 tokens gets 4 tokens.
        assert base_token.balanceOf(accounts[3]) == 4 * 10**18
        # Check that seller that wanted to sell 2 tokens sold 2 tokens.
        assert base_token.balanceOf(accounts[4]) == 0
        # Check that seller that wanted to sell 5 tokens sold 5 tokens.
        assert base_token.balanceOf(accounts[5]) == 0
        # Check that seller that wanted to sell 3 tokens sold 3 tokens.
        assert base_token.balanceOf(accounts[6]) == 0


    def test_onSwapTime_remainingHeap_moreSelling(daocross, base_token):
        """
        Check if after the token transfers, the remaining tokens are transfered to the owner of the tokens.

        Buying 10 tokens and selling 11.5 tokens.
        """
        n_tokens = [2, 5, 4.5]
        account_ind = [4, 5, 6]
        for n, ind in zip(n_tokens, account_ind):
            # Transfer the token to the users that will participate sell order.
            base_token.transfer(
                accounts[ind],
                n * 10**18,
                {"from": accounts[0], "gas_price": "60 gwei"},
            )
            # Approve the transfers for the contract.
            base_token.approve(
                daocross,
                n * 10**18,
                {"from": accounts[ind], "gas_price": "60 gwei"},
            )
            # Submit sell order.
            daocross.sellOrder(
                base_token.address,
                n * 10**18,
                100000000000,
                accounts[ind],
                {"from": accounts[ind], "gas_price": "60 gwei"},
            )
        # Buy 5 tokens for 100000000000 WEI.
        daocross.buyOrder(
            base_token.address,
            5 * 10**18,
            100000000000,
            accounts[1],
            {"from": accounts[1], "gas_price": "60 gwei", "value": 100000000000 * 5},
        )
        # Buy 2 tokens for 100000000000 WEI.
        daocross.buyOrder(
            base_token.address,
            2 * 10**18,
            100000000000,
            accounts[2],
            {"from": accounts[2], "gas_price": "60 gwei", "value": 100000000000 * 2},
        )
        # Buy 3 tokens for 100000000000 WEI.
        daocross.buyOrder(
            base_token.address,
            3 * 10**18,
            100000000000,
            accounts[3],
            {"from": accounts[3], "gas_price": "60 gwei", "value": 100000000000 * 3},
        )
        # Submit sell orders.
        daocross.onSwapTime({"from": accounts[0], "gas_price": "60 gwei"})
        # Check that user that wanted to buy 5 tokens gets 5 tokens.
        assert base_token.balanceOf(accounts[1]) == 5 * 10**18
        # Check that user that wanted to buy 2 tokens gets 2 tokens.
        assert base_token.balanceOf(accounts[2]) == 2 * 10**18
        # Check that user that wanted to buy 3 tokens gets 3 tokens.
        assert base_token.balanceOf(accounts[3]) == 3 * 10**18
        # Check that seller that wanted to sell 2 tokens sold 2 tokens.
        assert base_token.balanceOf(accounts[4]) == 0
        # Check that seller that wanted to sell 5 tokens sold only 3.5 and got 1.5 back.
        assert base_token.balanceOf(accounts[5]) == 1.5 * 10**18
        # Check that seller that wanted to sell 4.5 tokens sold 4.5 tokens.
        assert base_token.balanceOf(accounts[6]) == 0
