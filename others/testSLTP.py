from colorama import Fore, Back, Style
from pprint import pprint

from time import sleep, time

from binance.client import Client
from binance.exceptions import BinanceAPIException

import pandas_ta as ta

import json
import math
import time

import telegram_send

import pandas as pd     # needs pip install
import numpy as np
import matplotlib.pyplot as plt   # needs pip install
from operator import add
from operator import sub

from mpl_finance import candlestick2_ohlc

def get_data_frame(client, crypto, StartTime, Interval):
    # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    # request historical candle (or klines) data using timestamp from above, interval either every min, hr, day or month
    # starttime = '30 minutes ago UTC' for last 30 mins time
    # e.g. client.get_historical_klines(symbol='ETHUSDTUSDT', '1m', starttime)
    # starttime = '1 Dec, 2017', '1 Jan, 2018'  for last month of 2017
    # e.g. client.get_historical_klines(symbol='BTCUSDT', '1h', "1 Dec, 2017", "1 Jan, 2018")
    starttime = StartTime  # to start for 1 day ago
    interval = Interval
    bars = client_binance.futures_historical_klines(crypto, interval, starttime)
    #pprint.pprint(bars)
    
    for line in bars:        # Keep only first 5 columns, "date" "open" "high" "low" "close"
        del line[5:]
    df = pd.DataFrame(bars, columns=['date', 'open', 'high', 'low', 'close']) #  2 dimensional tabular data
    #df.set_index('date', inplace=True)
    
    for i in df.columns:
        df[i] = df[i].astype(float)

    df['date'] = pd.to_datetime(df['date'], unit='ms') 
    
    return df

def HA(df):
    df['HA_close']=(df['open']+ df['high']+ df['low']+df['close'])/4

    idx = df.index.name
    df.reset_index(inplace=True)

    for i in range(0, len(df)):
        if i == 0:
            df.at[i, 'HA_open'] = ((df.at[i, 'open'] + df.at[i, 'close']) / 2)
        else:
            df.at[i, 'HA_open'] = ((df.at[i - 1, 'HA_open'] + df.at[i - 1, 'HA_close']) / 2)

    if idx:
        df.set_index(idx, inplace=True)

    df['HA_high']=df[['HA_open','HA_close','high']].max(axis=1)
    df['HA_low']=df[['HA_open','HA_close','low']].min(axis=1)
    return df


def get_precision(client, symbol):
    global telegram_bot
    try:
        info = client.futures_exchange_info()
    except Exception as e:
        print(e)
        telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer la précision de la pair, peut-être un problème d'api, je m'arrête.")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
    
    for x in info['symbols']:
        if x['symbol'] == symbol:
            return x['quantityPrecision'], x['pricePrecision']

def round_decimals_down(number:float, decimals:int=2):
    """
    Returns a value rounded down to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return math.floor(number)

    factor = 10 ** decimals
    return math.floor(number * factor) / factor

if __name__ == "__main__":

    

    

    client_binance = Client('publickey', 'privatekey')
    info = client_binance.futures_exchange_info()
    for x in info['symbols']:
        if x['symbol'] == 'BTCUSDT':
            print(x)


    DataCrypto = get_data_frame(client_binance, 'BTCUSDT', '1 month ago',  '15m') #WOOUSDT #UNFIUSDT #UNIUSDT #TOMOUSDT


    DataCrypto = HA(DataCrypto)

    #PARAMETER
    leverage = 20
    pair = 'BTCUSDT'


    try:
        client_binance.futures_change_leverage(symbol=pair, leverage=int(leverage))
    except Exception as e:
        print(e)
        telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à changer le multiplicateur, peut-être un problème d'api, je m'arrête.")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

    
    precision, pricePrecision = get_precision(client_binance, pair)
    print("Pair and Precision :")
    print(pair + " " + str(precision))

    srcCloseElement = len(DataCrypto['close'])-1

    StopLossPrice = None
    TakeProfitPrice = None

    quantityUSDTTrade = 40

    while True:
        try:
            pairPrice = float(client_binance.futures_symbol_ticker(symbol=pair)['price'])
            break
        except Exception as e:
            print(e)
            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer le prix de la pair, si ça se reproduit trop de fois à la suite, veuillez me stopper.")
            pass

    quantityCryptoToBuy = quantityUSDTTrade * leverage / pairPrice
    quantityCryptoToBuy = round_decimals_down(quantityCryptoToBuy, int(precision))

    StopLossPrice = DataCrypto['HA_low'][srcCloseElement-2]
    print(StopLossPrice)
    StopLossMsg = StopLossPrice
    StopLossPrice = round_decimals_down(StopLossPrice, int(pricePrecision))
    print(StopLossPrice)
    TakeProfitPrice =  DataCrypto['HA_open'][srcCloseElement] + (((DataCrypto['HA_low'][srcCloseElement-2] - DataCrypto['HA_open'][srcCloseElement]) * 2) * -1.0)
    TakeProfitMsg = TakeProfitPrice
    TakeProfitPrice = round_decimals_down(TakeProfitPrice, int(pricePrecision));

    exit()

    
    res = client_binance.futures_create_order(symbol=pair, side='BUY', type='MARKET', quantity=quantityCryptoToBuy, reduceOnly=False)
    TradeOrderTime = res['updateTime']
        
    time.sleep(2)
    print(StopLossPrice)
    res = client_binance.futures_create_order(symbol=pair, side='SELL', type='STOP_MARKET', timeInForce='GTE_GTC', quantity=quantityCryptoToBuy, reduceOnly=True, stopPrice=StopLossPrice, workingType='MARK_PRICE')
            
        
    time.sleep(2)
    print(TakeProfitPrice)
    res = client_binance.futures_create_order(symbol=pair, side='SELL', type='TAKE_PROFIT_MARKET', timeInForce='GTE_GTC', quantity=quantityCryptoToBuy, reduceOnly=True, stopPrice=TakeProfitPrice, workingType='MARK_PRICE')
            
        
    lastPricetrade = pairPrice
    message = "[BOT] : J'ai pris un Trade Long. StopLoss = " + str(StopLossMsg) + " TakeProfit = " + str(TakeProfitMsg)
    telegram_bot.sendMessage(chat_id, message)
    print(res)
