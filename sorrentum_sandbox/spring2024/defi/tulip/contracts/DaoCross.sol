// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./PriceFeedOracle.sol";
import "./OrderMinHeap.sol";
import "./TwapVwapAdapter.sol";

import "../node_modules/@openzeppelin/contracts/access/Ownable.sol";
import "../node_modules/@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// @title Swap contract that allows trading large blocks of coins peer-to-peer.
contract DaoCross is Ownable {
    using OrderMinHeap for OrderMinHeap.Order;
    using OrderMinHeap for OrderMinHeap.Heap;

    // Declare the heaps as storage variables.
    OrderMinHeap.Heap private buyHeap;
    OrderMinHeap.Heap private sellHeap;

    // From https://docs.chain.link/data-feeds/price-feeds/addresses.
    PriceFeedOracle public priceFeedOracle;
    TwapVwapAdapter public twapVwapOracle;
    uint16 public swapPeriodInSecs;
    uint8 public swapRandomizationInSecs;
    uint8 public priceMode;
    uint256 public feesAsPct;
    string public baseTokenSymbol;
    // The ERC20 token to buy / sell relatively to ETH.
    IERC20 baseToken;

    OrderMinHeap.Order[] public orders;

    struct Transfer {
        address token;
        uint256 amount;
        address from;
        address to;
        bool isReturn;
    }

    // Events used to interact with frontend.
    event newBuyOrder(
        address baseToken,
        address quoteToken,
        uint256 amount,
        uint256 limitPrice,
        address depositAddress
    );
    event newSellOrder(
        address baseToken,
        address quoteToken,
        uint256 amount,
        uint256 limitPrice,
        address depositAddress
    );

    /// @param _baseToken: a token to swap (e.g., wBTC, ADA)
    /// @param _baseTokenSymbol: base token symbol to use with twap/vwap API
    /// @param _swapPeriodInSecs: how often to perform the swap (e.g., 300 to perform a swap every 5 minutes)
    /// @param _swapRandomizationInSecs: how many random seconds to add or subtract to the `swapPeriodsInSecs`.
    ///    E.g., _swapPeriodInSecs=300 and _swapRandomizationInSecs=5, it means that each swap happens every 5 minutes
    ///    with a different number of seconds in [0, 5] before or after the 5 minute mark.
    /// @param _feesAsPct: fees to charge in terms of value exchanged
    /// @param _priceMode: 1 for chainlink price feed, 2 for twap, 3 for vwap
    /// @param _priceFeedOracle: contract providing the price for the _baseToken from chainlink price feed
    /// @param _twapVwapOracle: contract providing the price for the _baseToken from our twap/vwap external adapter
    constructor(
        address _baseToken,
        string memory _baseTokenSymbol,
        uint16 _swapPeriodInSecs,
        uint8 _swapRandomizationInSecs,
        uint8 _feesAsPct,
        uint8 _priceMode,
        address _priceFeedOracle,
        address _twapVwapOracle
    ) {
        swapPeriodInSecs = _swapPeriodInSecs;
        swapRandomizationInSecs = _swapRandomizationInSecs;
        feesAsPct = _feesAsPct;
        baseTokenSymbol = _baseTokenSymbol;
        priceMode = _priceMode;
        // Deploy new price feed client contract.
        priceFeedOracle = new PriceFeedOracle(_priceFeedOracle);
        // Get the deployed contract of TwapVwap adapter.
        twapVwapOracle = TwapVwapAdapter(_twapVwapOracle);
        baseToken = IERC20(_baseToken);
    }

    /// @notice Create an order to buy the tokens for ETH
    /// @param _baseToken: the base ERC20 token
    /// @param _quantity: amount of token to buy with 18 decimals, e.g. 1 * 10**18 for 1 token
    /// @param _limitPrice: the max price for one token in WEI
    /// @param _depositAddress: the address to send the tokens after the order is completed
    function buyOrder(
        address _baseToken,
        uint256 _quantity,
        uint256 _limitPrice,
        address _depositAddress
    ) external payable {
        require(_baseToken == address(baseToken));
        uint256 fullPrice = (_quantity * _limitPrice) / 10 ** 18;
        require(
            msg.value >= fullPrice,
            "Value should cover the full price of requested amount of tokens"
        );
        OrderMinHeap.Order memory order = OrderMinHeap.Order(
            orders.length,
            msg.sender,
            _baseToken,
            address(0x0), // define ETH as zero addr
            _quantity,
            _limitPrice,
            true,
            _depositAddress,
            block.timestamp
        );
        orders.push(order);
        emit newBuyOrder(
            _baseToken,
            address(0x0),
            _quantity,
            _limitPrice,
            _depositAddress
        );
    }

    /// @notice Create an order to sell the tokens for ETH.
    /// @param _baseToken: amount of token to sell
    /// @param _quantity: amount of token to sell with 18 decimals, e.g. 1 * 10**18 for 1 token
    /// @param _limitPrice: the upper price for one token in WEI
    /// @param _depositAddress: the address to send the ETH after the order is completed
    function sellOrder(
        address _baseToken,
        uint256 _quantity,
        uint256 _limitPrice,
        address _depositAddress
    ) external payable {
        require(_baseToken == address(baseToken));
        // NOTE: User needs to approve the smart contract to spend their tokens.

        uint256 allowance = baseToken.allowance(msg.sender, address(this));
        require(allowance >= _quantity, "Check the token allowance");
        // Receive tokens.
        // It's better to recieve tokens straightaway as users can move tokens to different address
        // during the swap period and break calculated swap proportion.

        baseToken.transferFrom(msg.sender, address(this), _quantity);

        //
        OrderMinHeap.Order memory order = OrderMinHeap.Order(
            orders.length,
            msg.sender,
            _baseToken,
            address(0x0), // define ETH as zero addr
            _quantity,
            _limitPrice,
            false,
            _depositAddress,
            block.timestamp
        );
        orders.push(order);
        emit newSellOrder(
            _baseToken,
            address(0x0),
            _quantity,
            _limitPrice,
            _depositAddress
        );
    }

    /**
     * @notice Execute the swap.
     * @dev This function calculates the clearing price using the Chainlink price feed, matches orders based on the
     * calculated clearing price, and then executes transfers of Ether and tokens for the matched orders. After
     * executing the transfers, it erases all orders.
     */
    function onSwapTime() public onlyOwner {
        uint256 clearingPrice = getPrice();
        // Initialize the heaps.
        Transfer[] memory transfers = processOrders(clearingPrice);
        for (uint256 i = 0; i < transfers.length; i++) {
            Transfer memory transfer = transfers[i];
            if (transfer.token == address(0x0)) {
                // Send ETH.
                (bool sent, bytes memory data) = transfer.to.call{
                    value: transfer.amount
                }("");
                require(sent, "Failed to send Ether");
            } else {
                // Send tokens.
                require(transfer.token == address(baseToken));
                baseToken.transfer(transfer.to, transfer.amount);
            }
        }
        // We also need to return money to the users who paid extra?
        // To users whose order was not fully accomplished?
        eraseOrders();
    }

    /**
     * @notice Match buy and sell orders based on the clearing price.
     * @dev This function will create two heaps (buyHeap and sellHeap) based on the orders' limit prices and
     * the given clearing price. It will then successively compare the top elements of the two heaps and
     * match their quantities until either heap is empty. Finally, it will return an array of transfers
     * needed to fulfill the matched orders.
     * @param clearingPrice The price at which buy and sell orders are matched
     * @return transfers An array of Transfer structs representing the transfers needed to fulfill the matched orders
     */
    function processOrders(
        uint256 clearingPrice
    ) public returns (Transfer[] memory transfers) {
        OrderMinHeap.createHeap(buyHeap);
        OrderMinHeap.createHeap(sellHeap);
        // Prepare the array to hold transfers.
        transfers = new Transfer[](orders.length * 3);
        uint256 transferIndex = 0;
        // Filter out the orders that don't fit the price condition.
        transferIndex = filterOrders(clearingPrice, transfers, transferIndex);
        // Match the orders.
        transferIndex = matchOrders(clearingPrice, transfers, transferIndex);
        // Fill the returns for unmatched orders.
        transferIndex = returnLeftovers(transfers, transferIndex);
        // Resize the transfers array to match the actual number of transfers.
        Transfer[] memory resizedTransfers = new Transfer[](transferIndex);
        for (uint256 i = 0; i < transferIndex; i++) {
            resizedTransfers[i] = transfers[i];
        }
        // Return the transfers array.
        return resizedTransfers;
    }

    /**
     * @notice Filter orders based on the clearing price.
     * @dev Filters the orders based on their limit price in relation to the clearing price,
     * and inserts the valid orders into the appropriate buy or sell heap.
     * Returns the unmatched orders, either as ETH or ERC20 tokens, to the user.
     * @param clearingPrice The price at which buy and sell orders are matched
     * @param transfers The array of transfers to be updated with the return transfers for unmatched orders.
     * @param transferIndex the next available position in the transfers array
     * @return The next available index in the transfers array after adding the return transfers.
     */
    function filterOrders(
        uint256 clearingPrice,
        Transfer[] memory transfers,
        uint256 transferIndex
    ) private returns (uint256) {
        for (uint256 _index = 0; _index < orders.length; _index++) {
            OrderMinHeap.Order storage order = orders[_index];
            Transfer memory returnTransfer;
            if (order.isBuy == true) {
                if (order.limitPrice >= clearingPrice) {
                    OrderMinHeap.insert(buyHeap, order);
                } else {
                    // If the limit price user suggested and clearing price don't match
                    // we need to return ETH to the user.
                    returnTransfer = Transfer(
                        order.quoteToken, // for ETH we use zero address
                        (order.quantity * order.limitPrice) / 10 ** 18,
                        order.walletAddress,
                        order.depositAddress,
                        true
                    );
                    // Add the return to transfer array.
                    transfers[transferIndex++] = returnTransfer;
                }
            } else {
                if (order.limitPrice <= clearingPrice) {
                    OrderMinHeap.insert(sellHeap, order);
                } else {
                    // If the limit price user suggested and clearing price don't match
                    // we need to return ERC20 to the user.
                    returnTransfer = Transfer(
                        order.baseToken,
                        order.quantity,
                        order.walletAddress,
                        order.depositAddress,
                        true
                    );
                    // Add the return to transfer array.
                    transfers[transferIndex++] = returnTransfer;
                }
            }
        }
        return transferIndex;
    }

    /**
     * @notice Matches orders in the buyHeap and sellHeap and creates the corresponding transfers.
     * @dev Matches orders in the buyHeap and sellHeap and creates the corresponding transfers.
     * The function successively compares the top orders from the buyHeap and sellHeap, matches their
     * quantities until one of the heaps is empty or the orders cannot be matched anymore.
     *
     * @param clearingPrice The clearing price at which the orders are matched.
     * @param transfers The array of transfers that will store the base and quote token transfers.
     * @param transferIndex The index at which new transfers will be added to the transfers array.
     * @return The updated index of the transfers array after adding the matched transfers.
     */
    function matchOrders(
        uint256 clearingPrice,
        Transfer[] memory transfers,
        uint256 transferIndex
    ) private returns (uint256) {
        while (buyHeap.size > 0 && sellHeap.size > 0) {
            uint256 buyIndex = OrderMinHeap.topIndex(buyHeap);
            uint256 sellIndex = OrderMinHeap.topIndex(sellHeap);

            OrderMinHeap.Order storage buyOrder = orders[buyIndex];
            OrderMinHeap.Order storage sellOrder = orders[sellIndex];

            OrderMinHeap.removeTop(buyHeap);
            OrderMinHeap.removeTop(sellHeap);

            uint256 quantity = buyOrder.quantity < sellOrder.quantity
                ? buyOrder.quantity
                : sellOrder.quantity;

            Transfer memory baseTransfer = Transfer(
                buyOrder.baseToken,
                quantity,
                sellOrder.walletAddress,
                buyOrder.depositAddress,
                false
            );
            transfers[transferIndex++] = baseTransfer;

            Transfer memory quoteTransfer = Transfer(
                buyOrder.quoteToken,
                (quantity * clearingPrice) / 10 ** 18,
                buyOrder.walletAddress,
                sellOrder.depositAddress,
                false
            );
            transfers[transferIndex++] = quoteTransfer;

            buyOrder.quantity -= quantity;
            sellOrder.quantity -= quantity;

            if (buyOrder.quantity > 0) {
                OrderMinHeap.insert(buyHeap, buyOrder);
            }
            if (sellOrder.quantity > 0) {
                OrderMinHeap.insert(sellHeap, sellOrder);
            }
        }
        return transferIndex;
    }

    /**
     * @notice Processes the remaining orders and returns the unmatched quantities to the users.
     * @dev Processes the remaining orders in the buy or sell heap that were not matched,
     * and returns the unmatched quantities to the users, adds the returnt to transfers arrays
     * @param transferIndex the next available position in the transfers array.
     * @param transfers The array of transfers to be updated with the return transfers for unmatched orders.
     * @return The next available index in the transfers array after adding the return transfers.
     */
    function returnLeftovers(
        Transfer[] memory transfers,
        uint256 transferIndex
    ) private returns (uint256) {
        // Find the heap that is not empty.
        OrderMinHeap.Heap storage remainingHeap = buyHeap.size > 0
            ? buyHeap
            : sellHeap;

        while (remainingHeap.size > 0) {
            uint256 remainingIndex = OrderMinHeap.topIndex(remainingHeap);
            OrderMinHeap.Order memory remainingOrder = orders[remainingIndex];
            OrderMinHeap.removeTop(remainingHeap);
            Transfer memory remainingTransfer;
            if (remainingOrder.isBuy == true) {
                // Return ETH remained unmatched.
                remainingTransfer = Transfer(
                    remainingOrder.quoteToken, // for ETH we use zero address
                    (remainingOrder.quantity * remainingOrder.limitPrice) /
                        10 ** 18,
                    remainingOrder.walletAddress,
                    remainingOrder.depositAddress,
                    true
                );
            } else {
                // Return ERC20 remained unmatched.
                remainingTransfer = Transfer(
                    remainingOrder.baseToken,
                    remainingOrder.quantity,
                    remainingOrder.walletAddress,
                    remainingOrder.depositAddress,
                    true
                );
            }
            // Add the return to transfer array.
            transfers[transferIndex++] = remainingTransfer;
        }
        return transferIndex;
    }


    /// @notice Get token price from the Chainlink price feed or TwapVwap adapter. 
    function getPrice() public returns (uint256) {
        uint256 uintPrice;
        int256 currentTimestamp = int(block.timestamp);
        // Get the timestamp of one week before.
        int256 startTimestamp = currentTimestamp - 604800;
        if (priceMode == 1) {
            int256 price = priceFeedOracle.getLatestPrice();
            uintPrice = uint(price);
        } else if (priceMode == 2) {
            bytes32 requestId = twapVwapOracle.requestTwap(baseTokenSymbol, startTimestamp, currentTimestamp);
            uintPrice = twapVwapOracle.getResult(requestId);
        } else if (priceMode == 3) {
            bytes32 requestId = twapVwapOracle.requestVwap(baseTokenSymbol, startTimestamp, currentTimestamp);
            uintPrice = twapVwapOracle.getResult(requestId);
        }
        require(uintPrice > 0, "Price should be more than zero");
        return uintPrice;

    }

    function eraseOrders() internal onlyOwner {
        // Remove orders from the previous.
        delete orders;
        // Create new orders array.
        OrderMinHeap.Order[] storage orders;
    }
}
