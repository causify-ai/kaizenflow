# TODO(Juraj): brownie module not available in the current container version.
if False:
    import brownie
    import pytest


    @pytest.fixture(scope="module")
    def token(SorrentumToken, accounts):
        return SorrentumToken.deploy(
            "Sorrentum", "SORR", 100, 1000, {"from": accounts[0]}
        )


    @pytest.fixture(autouse=True)
    def shared_setup(fn_isolation):
        pass


    def test_transfer_sender_balance(accounts, token):
        balance = token.balanceOf(accounts[0])
        token.transfer(accounts[1], 10**18, {"from": accounts[0]})
        # Check whether the sender balance increased.
        assert token.balanceOf(accounts[0]) == balance - 10**18


    def test_transfer_receiver_balance(accounts, token):
        balance = token.balanceOf(accounts[1])
        token.transfer(accounts[1], 10**18, {"from": accounts[0]})
        # Check whether the reciever balance decreased.
        assert token.balanceOf(accounts[1]) == balance + 10**18


    def test_transfer_insufficient_balance(accounts, token):
        with brownie.reverts("ERC20: transfer amount exceeds balance"):
            token.transfer(accounts[2], 10**18, {"from": accounts[1]})


    def test_mint_more(accounts, token):
        balance = token.balanceOf(accounts[0])
        # Maximum supply is 1000, current supply is 100, so 900 tokens is a maximum we can mint.
        token.mint(accounts[0], 900, {"from": accounts[0]})
        # Check whether the new portion of tokes was minted.
        assert token.balanceOf(accounts[0]) == balance + 900 * 10**18


    def test_mint_more_max_supply_error(accounts, token):
        with brownie.reverts("Maximum supply has been reached"):
            token.mint(accounts[0], 901, {"from": accounts[0]})


    def test_mint_reverts_not_owner(accounts, token):
        with brownie.reverts("Ownable: caller is not the owner"):
            token.mint(accounts[1], 1, {"from": accounts[1]})
