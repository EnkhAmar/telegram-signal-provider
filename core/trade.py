import json
from dynamodb_json import json_util
from binance import Client
from binance.enums import *
from os import getenv
from typing import TypedDict, Literal, List

BINANCE_API_KEY = getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = getenv("BINANCE_API_SECRET")
client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)

class Signal(TypedDict):
    chat_id: int
    msg_id: int
    msg_text: str
    pair: str
    side: Literal["BUY", "SELL"]
    entry: float
    stop_loss: float
    take_profit: List[float]
    type: Literal["LIMIT", "MARKET"]
    order_id: str
    leverage: int
    action: Literal["NEW_SIGNAL"]

def get_symbol_config(symbol:str, symbols)->dict:
    return next(filter(lambda s: s['symbol'] == symbol, symbols), None)

def handler(event, context):
    exchange_info = client.futures_exchange_info()
    account_config = client.futures_account_config()
    account_info = client.futures_account()
    signal: Signal = json.loads(event['body'])

    symbol = signal['pair'].replace("/", "")

    if account_config['dualSidePosition']:
        client.futures_change_position_mode(dualSidePosition=False)

    position = next(filter(lambda p: p['symbol'] == symbol, account_info['positions']), None)
    current_leverage = int(position['leverage'])
    if float(position['positionAmt']) != 0:
        print(f"There is currently open positions on {symbol} with amount of {position['positionAmt']}")
        return

    symbol_config = get_symbol_config(symbol, exchange_info['symbols'])

    if signal['leverage'] != current_leverage:
        print("Need to change leverage")
        change_leverage_response = client.futures_change_leverage(symbol=symbol,leverage=signal['leverage'])
        print("change_leverage_response = ", change_leverage_response)

    take_profit_side = SIDE_SELL if signal['side'] == 'BUY' else SIDE_BUY
    stop_loss_side = SIDE_SELL if signal['side'] == 'BUY' else SIDE_BUY
    available_balance = float(account_info['availableBalance'])
    entry_price = signal['entry']
    take_profits = signal['take_profit']
    position_usdt = available_balance * 0.10
    quantity = round((position_usdt * signal['leverage']) / entry_price, symbol_config['quantityPrecision'])

    orders = [
        {
            'symbol': symbol,
            'side': signal['side'],
            'positionSide': 'BOTH',
            'type': FUTURE_ORDER_TYPE_LIMIT,
            'quantity': quantity,
            'price': round(entry_price, symbol_config['pricePrecision']),
            'timeInForce': TIME_IN_FORCE_GTC
        },
        {
            'symbol': symbol,
            'side': stop_loss_side,
            'positionSide': 'BOTH',
            'type': FUTURE_ORDER_TYPE_STOP_MARKET,
            'stopPrice': round(signal['stop_loss'], symbol_config['pricePrecision']),
            'quantity': quantity,
            'timeInForce': 'GTE_GTC',
            'reduceOnly': 'true',
        },
        {
            'symbol': symbol,
            'side': take_profit_side,
            'positionSide': 'BOTH',
            'type': FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
            'stopPrice': round(take_profits[-2], symbol_config['pricePrecision']),
            'quantity': round(quantity / 2, symbol_config['quantityPrecision']),
            'timeInForce': 'GTE_GTC',
            'reduceOnly': 'true'
        },
        {
            'symbol': symbol,
            'side': take_profit_side,
            'positionSide': 'BOTH',
            'type': FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
            'stopPrice': round(take_profits[-1], symbol_config['pricePrecision']),
            'quantity': round(quantity / 2, symbol_config['quantityPrecision']),
            'timeInForce': 'GTE_GTC',
            'reduceOnly': 'true'
        },
    ]
    for order in orders:
        resp = client.futures_create_order(**order)
        print("-"*16)
        print("order = ", order)
        print("resp = ", resp)