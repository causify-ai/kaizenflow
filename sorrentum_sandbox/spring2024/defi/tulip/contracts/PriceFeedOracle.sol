// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "../node_modules/@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

contract PriceFeedOracle {
    AggregatorV3Interface internal priceFeed;

    /// @param priceFeedAddr: contract address from https://docs.chain.link/data-feeds/price-feeds/addresses
    constructor(address priceFeedAddr) {
        priceFeed = AggregatorV3Interface(priceFeedAddr);
    }

    /// @notice Returns the latest price.
    function getLatestPrice() public view returns (int256) {
        /*
        roundId: The round ID of the latest data update. This is a unique identifier for each round of data.
        answer: The latest price as a signed integer, typically scaled by 1e8 (or 10^8) to accommodate decimal values.
        startedAt: The timestamp when the round started, returned as a Unix epoch time (in seconds).
        updatedAt: The timestamp when the round was last updated, returned as a Unix epoch time (in seconds).
        answeredInRound: The round ID in which the answer was computed.
        */
        (
            ,
            /* uint80 roundID */ int256 price,
            ,
            ,

        ) = /*uint startedAt*/ /*uint updatedAt*/ /*uint80 answeredInRound*/
            priceFeed.latestRoundData();
        return price;
    }
}
