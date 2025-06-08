from binance import Client
from os import getenv
from dotenv import load_dotenv

load_dotenv()

BINANCE_API_KEY = getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = getenv("BINANCE_API_SECRET")

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)

print(client.futures_account_balance())

print(client.futures_account())