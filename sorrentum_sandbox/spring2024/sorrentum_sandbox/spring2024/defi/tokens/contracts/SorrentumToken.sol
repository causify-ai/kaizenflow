// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import "../node_modules/@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "../node_modules/@openzeppelin/contracts/access/Ownable.sol";

contract SorrentumToken is ERC20, Ownable {
    uint256 public MAXIMUM_SUPPLY;

    constructor(string memory name, string memory symbol, uint256 amountPreMint, uint256 maxSupply) ERC20(name, symbol) {
        MAXIMUM_SUPPLY = maxSupply * 10**decimals();
        amountPreMint = amountPreMint * 10**decimals();
        require(amountPreMint <= MAXIMUM_SUPPLY, "Premint amount is more than maximum supply");
        // Premint.
        _mint(msg.sender, amountPreMint);
    }

    function mint(address to, uint256 amount) external onlyOwner {
        amount = amount * 10**decimals();
        require((totalSupply()+amount)<=MAXIMUM_SUPPLY, "Maximum supply has been reached");
        _mint(to, amount);
    }
}
