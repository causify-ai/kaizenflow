from brownie import Token, accounts


def main():
    token = Token.deploy("Test Token", "TST", 18, 1e23, {"from": accounts[0]})
    return token


def distribute_tokens(sender=accounts[0], receiver_list=accounts[1:]):
    token = main()
    for receiver in receiver_list:
        token.transfer(receiver, 1e18, {"from": sender})
