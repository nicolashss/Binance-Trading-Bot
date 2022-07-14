# pip install tradingview_ta --upgrade

from tradingview_ta import TA_Handler, Interval, Exchange
import tradingview_ta
import time
from colorama import Fore
import sys
import os

if os.name == 'nt':
    os.system('cls')

else:
    os.system('clear')

print(">> Version de l'API: " + tradingview_ta.__version__)

handler = TA_Handler(
    symbol="BTCUSDT",
    exchange="binance",
    screener="crypto",
    interval=Interval.INTERVAL_5_MINUTES,
)

print('-------------------------------')

print(handler.get_analysis().oscillators)
print(handler.get_analysis().moving_averages)

print('-------------------------------')

print(handler.get_analysis().summary)