import json
from binance import Client
from os import getenv
from dotenv import load_dotenv

load_dotenv()

BINANCE_API_KEY = getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = getenv("BINANCE_API_SECRET")

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)
exchange_info = client.futures_exchange_info()

symbol = 'BTCUSDT'

def get_symbol_config(symbol:str) -> dict:
    return next(filter(lambda s: s['symbol'] == symbol, exchange_info['symbols']), None)


account_info = client.futures_account()
availableBalance = account_info['availableBalance']

account_config = client.futures_account_config()
print("account_config = ", account_config)
# if account_config['dualSidePosition']:
#     client.futures_change_position_mode(dualSidePosition=False)

# assets = filter(lambda a: a[''], account_info['assets'])
signal = {'chat_id': -1001338521686, 'msg_id': 8151, 'msg_text': 'BTC/USDT 📈 BUY\n\n🔹Enter above:\xa0102501.6(with a maximum value 102550.0)\n\n💰TP1 102919.8\n💰TP2 103533.6\n💰TP3 105736.8\n🚫SL 101233.3\n\n〽️Leverage 10x\n\n⚠️Respect the entry zone. Check the bio of the channel for all the info required to follow our signals\n\n📍Bybit, Binance, Bitget', 'pair': 'BTC/USDT', 'side': 'BUY', 'entry': 102501.6, 'stop_loss': 101233.3, 'take_profit': [102919.8, 103533.6, 105736.8], 'action': 'NEW_SIGNAL', 'type': 'LIMIT', 'order_id': '-1001338521686_8151', 'leverage': 10} 


# print(account_info['assets'][-1])

# signal_leverage = 20

position = next(filter(lambda p: p['symbol'] == symbol, account_info['positions']), None)
current_leverage = int(position['leverage'])
print("position---\n")
print(position)
{'symbol': 'BTCUSDT', 'initialMargin': '512.66351999', 'maintMargin': '20.50654080', 'unrealizedProfit': '-0.05013333', 'positionInitialMargin': '512.66351999', 'openOrderInitialMargin': '0', 'leverage': '10', 'isolated': True, 'entryPrice': '106805.9444444', 'breakEvenPrice': '106899.5560707', 'maxNotional': '40000000', 'positionSide': 'BOTH', 'positionAmt': '0.048', 'notional': '5126.63520000', 'isolatedWallet': '515.93868217', 'updateTime': 1750843044222, 'bidNotional': '0', 'askNotional': '0'}
print("\n\n\n")


# if signal_leverage != current_leverage:
#     print("Need to change leverage")
#     change_leverage_response = client.futures_change_leverage(symbol=symbol,leverage=signal_leverage)
#     print("change_leverage_response = ", change_leverage_response)


# Place batch order to create with TP and SL
# client.futures_place_batch_order(
#     batchOrders=[]
# )

from binance.enums import *
available_balance = float(account_info['availableBalance'])
entry_price = 105000.6
stop_loss = 105740.6
take_profits = [102919.8, 103533.6, 105736.8]
take_profits = [106810.6, 106820.6, 106850.6]
leverage = 10
symbol = 'BTCUSDT'
side = SIDE_BUY

symbol_config = get_symbol_config(symbol)
print(symbol_config)

# Change leverage
signal_leverage = leverage
if signal_leverage != current_leverage:
    print("Need to change leverage")
    change_leverage_response = client.futures_change_leverage(symbol=symbol,leverage=signal_leverage)
    print("change_leverage_response = ", change_leverage_response)

# Calculate 10% of balance to use
position_usdt = available_balance * 0.10
quantity = round((position_usdt * leverage) / entry_price, symbol_config['quantityPrecision'])  # Adjust precision based on symbol rules

print('quantity = ', quantity)

orders = [
    # 1. Main LIMIT entry order
    {
        'symbol': symbol,
        'side': SIDE_BUY,
        'positionSide': 'BOTH',
        # 'type': FUTURE_ORDER_TYPE_LIMIT,
        'type': FUTURE_ORDER_TYPE_MARKET,
        'quantity': quantity,
        # 'price': round(entry_price, symbol_config['pricePrecision']),
        # 'timeInForce': TIME_IN_FORCE_GTC
    },

    # 2. Stop Loss
    {
        'symbol': symbol,
        'side': SIDE_SELL,
        'positionSide': 'BOTH',
        'type': FUTURE_ORDER_TYPE_STOP_MARKET,
        'stopPrice': round(stop_loss, symbol_config['pricePrecision']),
        'quantity': quantity,
        # 'closePosition': True,
        'timeInForce': 'GTE_GTC',
        'reduceOnly': "true"
    },

    # 3. TP1
    {
        'symbol': symbol,
        'side': SIDE_SELL,
        'positionSide': 'BOTH',
        'type': 'TAKE_PROFIT_MARKET',
        'stopPrice': round(take_profits[0], symbol_config['pricePrecision']),
        'quantity': round(quantity / 3, symbol_config['quantityPrecision']),
        'timeInForce': 'GTE_GTC',
        'reduceOnly': 'true'
    },

    # 4. TP2
    {
        'symbol': symbol,
        'side': SIDE_SELL,
        'positionSide': 'BOTH',
        'type': FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
        'stopPrice': round(take_profits[1], symbol_config['pricePrecision']),
        'quantity': round(quantity / 3, symbol_config['quantityPrecision']),
        'timeInForce': 'GTE_GTC',
        'reduceOnly': 'true'
    },

    # 5. TP3
    {
        'symbol': symbol,
        'side': SIDE_SELL,
        'positionSide': 'BOTH',
        'type': FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
        'stopPrice': round(take_profits[2], symbol_config['pricePrecision']),
        'quantity': round(quantity / 3, symbol_config['quantityPrecision']),
        'timeInForce': 'GTE_GTC',
        'reduceOnly': 'true'
    }
]

# # Submit batch order
# response = client.futures_place_batch_order(batchOrders=orders)
# print("response = ", response)


# response = client.futures_create_order(
#     **orders[0]
# )
# print("response = ", response)
# response = client.futures_create_order(
#     **orders[1]
# )
# print("response = ", response)
# response = client.futures_create_order(
#     **orders[2]
# )
# print("response = ", response)
# response = client.futures_create_order(
#     **orders[3]
# )
# print("response = ", response)
# response = client.futures_create_order(
#     **orders[4]
# )
# print("response = ", response)