// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "../node_modules/@chainlink/contracts/src/v0.8/ChainlinkClient.sol";

contract TwapVwapAdapter is ChainlinkClient {
    using Chainlink for Chainlink.Request;
    address private oracle;
    bytes32 private jobIdTwap;
    bytes32 private jobIdVwap;

    uint256 private fee;
    mapping(bytes32 => uint256) requestIdToResult;
 

    
    constructor() {
        address sepoliaLINKContract = 0x779877A7B0D9E8603169DdbD7836e478b4624789;
        setChainlinkToken(sepoliaLINKContract);
        oracle = 0xa07c906a6c9eDCb21a03943586e8920D2d716E3D;
        jobIdTwap = stringToBytes32("75d8ce9d26db4edc942b878b1c89ac05");
        jobIdVwap = stringToBytes32("e3202058df5c4feea73fcf2c705a2fda");
        fee = 0.1 * 1*10**18;
    }
    
    function requestTwap(string memory _symbol, int256 _startTimestamp, int256 _endTimestamp) public returns (bytes32 requestId) {
        Chainlink.Request memory request = buildChainlinkRequest(jobIdTwap, address(this), this.fulfill.selector);
        // Set the parameters.
        request.add("symbol", _symbol);
        request.addInt("start_time", _startTimestamp);
        request.addInt("end_time", _endTimestamp);
        return sendChainlinkRequestTo(oracle, request, fee);
    }

    function requestVwap(string memory _symbol, int256 _startTimestamp, int256 _endTimestamp) public returns (bytes32 requestId) {
        Chainlink.Request memory request = buildChainlinkRequest(jobIdVwap, address(this), this.fulfill.selector);
        // Set the parameters.
        request.add("symbol", _symbol);
        request.addInt("start_time", _startTimestamp);
        request.addInt("end_time", _endTimestamp);
        return sendChainlinkRequestTo(oracle, request, fee);
    }
    
    function fulfill(bytes32 _requestId, uint256 _price) public recordChainlinkFulfillment(_requestId) {
        requestIdToResult[_requestId] = _price;
    }

    function getResult(bytes32 _requestId) public view returns (uint256) {
        return requestIdToResult[_requestId];
    }
    
    function stringToBytes32(string memory source) private pure returns (bytes32 result) {
        bytes memory tempEmptyStringTest = bytes(source);
        if (tempEmptyStringTest.length == 0) {
            return 0x0;
        }
        assembly { // solhint-disable-line no-inline-assembly
            result := mload(add(source, 32))
        }
    }
}