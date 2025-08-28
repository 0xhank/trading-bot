import getpass
import json
import os

import eth_account
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from lib.logger import get_trading_logger

logger = get_trading_logger()


def setup(base_url=None, skip_ws=False, perp_dexs=None):
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
    with open(config_path) as f:
        config = json.load(f)
    account: LocalAccount = eth_account.Account.from_key(config["private_key"])
    address = config["account_address"]
    if address == "":
        address = account.address
    logger.info(f"Running with account address: {address}")
    if address != account.address:
        logger.info(f"Running with agent address: {account.address}")
    info = Info(base_url, skip_ws, perp_dexs=perp_dexs)
    user_state = info.user_state(address)
    spot_user_state = info.spot_user_state(address)
    margin_summary = user_state["marginSummary"]
    if float(margin_summary["accountValue"]) == 0 and len(spot_user_state["balances"]) == 0:
        logger.warning("Not running the example because the provided account has no equity.")
        url = info.base_url.split(".", 1)[1]
        error_string = f"No accountValue:\nIf you think this is a mistake, make sure that {address} has a balance on {url}.\nIf address shown is your API wallet address, update the config to specify the address of your account, not the address of the API wallet."
        raise Exception(error_string)
    exchange = Exchange(account, base_url, account_address=address, perp_dexs=perp_dexs)
    return address, info, exchange

