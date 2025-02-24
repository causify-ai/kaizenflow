from brownie import Token, accounts


def main():
    acct = accounts.load("goerli")
    Token.deploy("My Real Token", "RLT", 18, 1e28, {"from": acct})
