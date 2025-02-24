// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import "../../tokens/contracts/SorrentumTokenETF.sol";
//import "../node_modules/@openzeppelin/contracts/access/Ownable.sol";

/// TODO(Toma): from GPs comment
/// 1) The user that creates the DaoETF contract should have a special interface, 
/// e.g., to liquidate the entire ETF, maybe some admin functions.

/// 2) The DaoEtfCreator should be able to specify an "investment" strategy. 
/// A super simple one is "invest the ETH from the user in N tokens maintaining 
/// a certain percentage, e.g., 50% ETH and 50% wBTC, rebalancing every week".
/// A complex one is "we shovel C1b system inside and trade furiously".
/// I think we need another Contract like "InvestmentStrategy" to pass to DaoETF.

/// @title An investment pool contract backed by a passive or active trading strategy. 
/// @notice Implement the logic for staking and redeeming tokens in the investment pool.
contract DaoETF is Ownable {

  SorrentumTokenETF public sorrToken;
  string public contractName;
  uint256 public sorrTokensPerEth = 1;

  event Invest(address buyer, uint256 amountOfETH, uint256 amountOfTokens);
  event Redeem(address seller, uint256 amountOfTokens, uint256 amountOfETH);

  /// @notice Deploy the ERC20 token contract.
  /// @param trackingTokenName the full name of token, e.g. `Sorrentum token`
  /// @param trackingTokenSymbol symbol of token that is used to track fractional ownership of the pool (e.g., SORRE)
  /// @param _contractName the name of the current contract
  constructor(string memory trackingTokenName, string memory trackingTokenSymbol, string memory _contractName) {
    sorrToken = new SorrentumTokenETF(trackingTokenName, trackingTokenSymbol);
    contractName = _contractName;
  }

  /// @notice Allow user to invest a token (e.g., ETH) and get back a tracking token (e.g., SORRE).
  function invest() public payable returns (uint256 amountToGet) {
    require(msg.value > 0, "Send ETH to get tokens");
    amountToGet = msg.value * sorrTokensPerEth;
    // Mint to the user.
    sorrToken.mint(msg.sender, amountToGet);
    // Emit the event.
    emit Invest(msg.sender, msg.value, amountToGet);
    return amountToGet;
  }

  /// @notice Allow user to redeem some of the tracking token (e.g., SORRE) for another token (e.g., ETH). 
  /// @notice Burns ERC20 token for redeem
  /// @param tokenAmountToSell amount to sell in WEI
  function redeem(uint256 tokenAmountToSell) public {
    require(tokenAmountToSell > 0, "Specify an amount of token to redeem greater than zero");
    // Check that the user's token balance is enough to do the swap.
    uint256 userBalance = sorrToken.balanceOf(msg.sender);
    ///TODO(Toma): add user address to the error message.
    require(userBalance >= tokenAmountToSell, "Your balance is lower than the amount of tokens you want to return");
    // Check that the contract balance is enough to do the swap.
    uint256 amountToTransfer = tokenAmountToSell / sorrTokensPerEth;
    uint256 ownerBalance = address(this).balance;
    ///TODO(Toma): remove this check later.
    require(ownerBalance >= amountToTransfer, "Contract has not enough funds to accept the request, try later");
    // Burn tokens.
    sorrToken.burn(msg.sender, tokenAmountToSell);
    // Send ETH back to user.
    (bool sent,) = msg.sender.call{value: amountToTransfer}("");
    ///TODO(Toma): add user address to the error message.
    require(sent, "Failed to send ETH to the user");
    emit Redeem(msg.sender, tokenAmountToSell, amountToTransfer);
  }

  /// @notice Withdraw ETH to owner address 
  /// @param amountToWithdraw amount to withdraw in WEI
  /// TODO(Toma): remove this method, we can maybe have methods like "pause", "stopInvesting"
  function withdraw(uint256 amountToWithdraw) public onlyOwner {
    // Withdraw from the pool to owner's address
    uint256 daoBalance = address(this).balance;
    require(daoBalance >= amountToWithdraw, "Not enough ETH in DaoETF");
    (bool sent,) = msg.sender.call{value: amountToWithdraw}("");
    require(sent, "Failed to send the balance to the owner");
  }

  /// @notice Get ERC20 user balance
  /// @param user user address
  /// TODO(Toma): should we also have a method to get info on what's in the DaoETF?
  function getUserTokenBalance(address user) external view returns (uint256 userBalance) {
    userBalance = sorrToken.balanceOf(user);
    return userBalance;
  }
}

