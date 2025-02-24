// SPDX-License-Identifier: MIT
pragma solidity ^0.8.9;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract Surrentum_v1 is ERC20, Ownable {
    constructor() ERC20("Surrentum Utility Token v1", "SURRE") {
        _mint(msg.sender, 10 * 10 ** decimals());
    }
}
