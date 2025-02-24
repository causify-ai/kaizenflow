pragma solidity ^0.8.0;


import "../node_modules/@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../node_modules/@openzeppelin/contracts/access/Ownable.sol";


contract TokenTimelock is Ownable {

    IERC20 public immutable token;

    mapping(address => Participant) participants;

    struct Participant {
        // Amount of tokens without with 18 decimals, e.g. 1000000000000000000 for 1 token.
        uint256 amount;
        // Unix timestamp (e.g., 1677064547 for Wed Feb 22 2023 11:15:47 GMT+0000) 
        // for when to release the amount of token.
        uint256 releaseTimestamp;
        // If the token was released.
        bool released;
    }

    constructor(address _token) {
        token = IERC20(_token);
    }

    function addParticipant(address _addr, uint256 _amount, uint256 _releaseTimestamp) public onlyOwner {
        require(participants[_addr].amount == 0, "This user already exists.");
        Participant memory participant = Participant(_amount, _releaseTimestamp, false);
        participants[_addr] = participant;
    }


    function addAmount(address _addr, uint256 _amount) public onlyOwner {
        // Add more tokens to the participant.
        require(participants[_addr].amount != 0, "This user doesn't exist.");
        Participant storage participant = participants[_addr]; 
        participant.amount += _amount;
    }

    function getReleaseTimestamp(address _addr) external view returns (uint256) {
        require(participants[_addr].amount != 0, "The user does not participate.");
        return participants[_addr].releaseTimestamp;
    }

    function getTokensAmountLocked(address _addr) external view returns (uint256) {
        require(participants[_addr].amount != 0, "The user does not participate.");
        return participants[_addr].amount;
    }

    function releaseTokens() external {
        require(participants[msg.sender].amount != 0, "The sender does not participate.");
        require(participants[msg.sender].releaseTimestamp < block.timestamp, "Release time hasn't come yet");
        require(participants[msg.sender].released == false, "Tokens are already released");
        // Update the release status.
        Participant storage participant = participants[msg.sender]; 
        participant.released = true;
        // Release tokens.
        token.transfer(msg.sender, participants[msg.sender].amount);
    }
    
    function withdrawTokens(uint256 _amount) external onlyOwner {
        token.transfer(owner(), _amount);
    }

    function getContractBalance() external view returns (uint256) {
        return token.balanceOf(address(this));

    }

}