// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import "../node_modules/@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "../node_modules/@openzeppelin/contracts/access/Ownable.sol";

contract SorrentumTokenETF is ERC20, Ownable {
    constructor(string memory name, string memory symbol) ERC20(name, symbol) {}

    /// @notice Mint the token to user address
    /// @param userAddr user address
    /// @param amount the amount of tokens to mint
    function mint(address userAddr, uint256 amount) public onlyOwner {
        _mint(userAddr, amount);
    }

    /// @notice Burn user tokens
    /// @param userAddr user address
    /// @param amount the amount of tokens to burn
    function burn(address userAddr, uint256 amount) public onlyOwner {
        _burn(userAddr, amount);
    }
}
