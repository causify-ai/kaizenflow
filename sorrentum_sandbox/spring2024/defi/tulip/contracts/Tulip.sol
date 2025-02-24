// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./PriceFeedOracle.sol";
import "./TwapVwapAdapter.sol";

import "../node_modules/@openzeppelin/contracts/access/Ownable.sol";
import "../node_modules/@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract Tulip is Ownable {

    // The ERC20 token to buy / sell for ETH.
    IERC20 baseToken;
    // From https://docs.chain.link/data-feeds/price-feeds/addresses.
    PriceFeedOracle public priceFeedOracle;
    // The contract that communicates with coingecko API through chainlink node and our external adapter.
    TwapVwapAdapter public twapVwapOracle;
    string public baseTokenSymbol;
    //uint16 public swapPeriodInSecs;
    //uint8 public swapRandomizationInSecs;
    //uint256 public feesAsPct;
    uint8 public priceMode;
    // The numerical ID of unique swap pair, e.g. wBTC/ETH.
    uint16 public pairID;
    // The ID of the current swap, is incremented after the swap is done.
    uint256 public currentSwapID;
    // The ID of the current order, is incremented after the order is submitted.
    uint256 public currentOrderID;
    // Store the ID of orders from the current swap.
    uint256[] ordersID;
    bytes32 priceRequestID;

    // .
    event newBuyOrder(
        uint256 indexed swapID,
        uint256 indexed orderID,
        address baseToken,
        address quoteToken,
        uint256 amount,
        uint256 limitPrice,
        address depositAddress,
        address senderAddress,
        uint16 pairID

    );
    event newSellOrder(
        uint256 indexed swapID,
        uint256 indexed orderID,
        address baseToken,
        address quoteToken,
        uint256 amount,
        uint256 limitPrice,
        address depositAddress,
        address senderAddress,
        uint16 pairID
    );

    event buyOrderDone();
    event sellOrderDone();


    /// @param _baseToken: a token to swap (e.g., wBTC, ADA)
    /// @param _baseTokenSymbol: base token symbol to use with twap/vwap API
    /// @param _pairID: The numerical ID of unique swap pair, e.g. wBTC/ETH.
    /// @param _priceMode: 1 for chainlink price feed, 2 for twap, 3 for vwap
    /// @param _priceFeedOracle: contract providing the price for the _baseToken from chainlink price feed
    /// @param _twapVwapOracle: contract providing the price for the _baseToken from our twap/vwap external adapter
    constructor(
        address _baseToken,
        string memory _baseTokenSymbol,
        uint16 _pairID,
        uint8 _priceMode,
        address _priceFeedOracle,
        address _twapVwapOracle
    ) {
        baseTokenSymbol = _baseTokenSymbol;
        priceMode = _priceMode;
        pairID = _pairID;
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
    ) external payable returns (uint256) {
        require(_baseToken == address(baseToken));
        uint256 fullPrice = (_quantity * _limitPrice) / 10 ** 18;
        require(
            msg.value >= fullPrice,
            "Value should cover the full price of requested amount of tokens"
        );
        emit newBuyOrder(
            currentSwapID,
            currentOrderID,
            _baseToken,
            address(0x0),
            _quantity,
            _limitPrice,
            _depositAddress,
            msg.sender,
            pairID
        );
        ordersID.push(currentOrderID);
        // Return the value and increment it after.
        return currentOrderID++;
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
    ) external payable returns (uint256) {
        require(_baseToken == address(baseToken));
        // NOTE: User needs to approve the smart contract to spend their tokens.
        uint256 allowance = baseToken.allowance(msg.sender, address(this));
        require(allowance >= _quantity, "Check the token allowance");
        // Receive tokens.
        baseToken.transferFrom(msg.sender, address(this), _quantity);
        emit newSellOrder(
            currentSwapID,
            currentOrderID,
            _baseToken,
            address(0x0),
            _quantity,
            _limitPrice,
            _depositAddress,
            msg.sender,
            pairID
        );
        ordersID.push(currentOrderID);
        // Return the value and increment it after.
        return currentOrderID++;
    }


    function runSwap() public returns (uint256) {
        return currentSwapID++;
    }


    function extractPrice() public view returns (uint256) {
        return twapVwapOracle.getResult(priceRequestID);
    }

    /// @notice Get token price from the Chainlink price feed or TwapVwap adapter. 
    function requestPrice() public {
        // Get the timestamp of the current block.
        int256 currentTimestamp = int(block.timestamp);
        // Get the timestamp of one week before.
        int256 startTimestamp = currentTimestamp - 604800;
        bytes32 requestId;
        if (priceMode == 1) {
            // Get twap price from coingecko API.
            requestId = twapVwapOracle.requestTwap(baseTokenSymbol, startTimestamp, currentTimestamp);
        } else if (priceMode == 2) {
            // Get VWAP price from coingecko API.
            requestId = twapVwapOracle.requestVwap(baseTokenSymbol, startTimestamp, currentTimestamp);
        }
        priceRequestID = requestId;
    }

    function eraseOrders() internal onlyOwner {
        // Remove orders from the previous swap.
        delete ordersID;
        // Create new orders array.
        uint256[] storage ordersID;
    }


}