// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import "../node_modules/@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "../node_modules/@openzeppelin/contracts/access/Ownable.sol";

/// @title A Mock ERC20 contract
/// @author Samarth
/// @notice Mock Contract for testing TokenTimeLock contract using brownie scripts
contract MockERC20 is ERC20, Ownable {
    uint256 public maxSupply;

    constructor(string memory name, string memory symbol, uint256 initialSupply, uint256 _maxSupply) ERC20(name, symbol) {
        maxSupply = _maxSupply * 10**decimals();
        initialSupply = initialSupply * 10**decimals();
        require(initialSupply <= maxSupply, "Premint amount is more than maximum supply");
        _mint(msg.sender, initialSupply);
    }
}
