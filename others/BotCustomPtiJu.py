import os
import sys

from colorama import init, Fore, Back, Style
from pprint import pprint

from time import sleep, time

from binance.client import Client
from binance.exceptions import BinanceAPIException

import pandas_ta as ta

import json
import math
import time

import telepot

import pandas as pd     # needs pip install
import numpy as np
import matplotlib.pyplot as plt   # needs pip install
from operator import add
from operator import sub

from datetime import datetime

import yaml

#GLOBAL
Telegram_Start_Command_Triggered = False
Telegram_Pair = "None"
Telegram_TradeAmount = -1.0
Telegram_Leverage = -1
TelegramStopSignal = False
Telegram_LastTradeStop = False
telegram_bot = None
chat_id = None


#CALCULATION AND DATA FUNCTION

def get_data_frame(client, crypto, StartTime, Interval):
    global telegram_bot
    # valid intervals - 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    # request historical candle (or klines) data using timestamp from above, interval either every min, hr, day or month
    # starttime = '30 minutes ago UTC' for last 30 mins time
    # e.g. client.get_historical_klines(symbol='ETHUSDTUSDT', '1m', starttime)
    # starttime = '1 Dec, 2017', '1 Jan, 2018'  for last month of 2017
    # e.g. client.get_historical_klines(symbol='BTCUSDT', '1h', "1 Dec, 2017", "1 Jan, 2018")
    starttime = StartTime  # to start for 1 day ago
    interval = Interval
    while True:
        try:
            bars = client_binance.futures_historical_klines(crypto, interval, starttime)
            break
        except Exception as e:
            print(e)
            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer les Bougies de Binance, si ça se reproduit trop de fois à la suite, veuillez me stopper.")
            pass
    #pprint.pprint(bars)
    
    for line in bars:        # Keep only first 5 columns, "date" "open" "high" "low" "close"
        del line[5:]
    df = pd.DataFrame(bars, columns=['date', 'open', 'high', 'low', 'close']) #  2 dimensional tabular data
    #df.set_index('date', inplace=True)
    
    for i in df.columns:
        df[i] = df[i].astype(float)

    df['date'] = pd.to_datetime(df['date'], unit='ms') 
    
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

def getUSDTBalanceSTR():
    global telegram_bot
    try:
        acc_balance = client_binance.futures_account_balance()
    except Exception as e:
        print(e)
        telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer le montant de ta balance USDT, peut-être un problème d'api, je m'arrête.")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
    
    for i in range(len(acc_balance)) :
        if acc_balance[i]['asset'] == 'USDT':
            return acc_balance[i]['balance']

    return 'NULL'

#CALCULATION AN DATA FUNCTION END




def get_API():

    try:
        yaml_file = open("./api.yaml", 'r')
    except:
        print(Fore.RED + "[ERREUR] :")
        print(Fore.WHITE + "Le fichier api.yaml n'existe pas ou n'est pas au bon endroit")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
    
    

    yaml_content = yaml.safe_load(yaml_file)
    return yaml_content




def handle_TELEGRAM_COMMAND(msg):
    
    global Telegram_Start_Command_Triggered
    global Telegram_Pair
    global Telegram_TradeAmount
    global Telegram_Leverage
    global TelegramStopSignal
    global Telegram_LastTradeStop
    global telegram_bot
    global chat_id

    chat_id = msg['chat']['id']
    command = msg['text']

    if command == 'command start':
        if Telegram_Pair == "None" :
            telegram_bot.sendMessage(chat_id, "[BOT] : Tu n'as pas rentré de pair, je ne peux pas démarrer")
        elif Telegram_TradeAmount == -1.0:
            telegram_bot.sendMessage(chat_id, "[BOT] : Tu n'as pas rentré de mise, je ne peux pas démarrer")
        elif Telegram_Leverage == -1:
            telegram_bot.sendMessage(chat_id, "[BOT] : Tu n'as pas rentré de multiplicateur, je ne peux pas démarrer")
        else :
            telegram_bot.sendMessage(chat_id, "[BOT] : Je démarre.")
            Telegram_Start_Command_Triggered = True

    elif command == 'command info':
        message = "[BOT] : La pair actuelle est : " + str(Telegram_Pair) + ". La mise actuelle est : " + str(Telegram_TradeAmount) + ". Le multiplicateur actuelle est : " + str(Telegram_Leverage) + "."
        telegram_bot.sendMessage(chat_id, message)
        #os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

    elif command == 'command stop':
        telegram_bot.sendMessage(chat_id, "[BOT] : Je m'arrête. à plus dans le bus")
        #os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
        TelegramStopSignal = True

    elif command == 'command ping':
        telegram_bot.sendMessage(chat_id, "[BOT] : pong")

    elif command.find('command set_pair') != -1 :
        arguments = command[17:]
        Telegram_Pair = str(arguments)
        message = "[BOT] : La pair est mise à jour : " + str(Telegram_Pair)
        telegram_bot.sendMessage(chat_id, message)

    elif command.find('command set_trade_amount') != -1 :
        arguments = command[25:]
        Telegram_TradeAmount = float(arguments)
        message = "[BOT] : La mise est mise à jour : " + str(Telegram_TradeAmount)
        telegram_bot.sendMessage(chat_id, message)

    elif command.find('command set_leverage') != -1 :
        arguments = command[21:]
        Telegram_Leverage = int(arguments)
        message = "[BOT] : Le multiplicateur est mis à jour : " + str(Telegram_Leverage)
        telegram_bot.sendMessage(chat_id, message)

    elif command == 'command last_trade_stop':
        telegram_bot.sendMessage(chat_id, "[BOT] Ok, je m'arrête à la fin du trade :) (ou de suite si y a pas de trade en cours)")
        Telegram_LastTradeStop = True


def WMA(s, period):
       return s.rolling(period).apply(lambda x: ((np.arange(period)+1)*x).sum()/(np.arange(period)+1).sum(), raw=True)

def HMA(s, period):
       return WMA(WMA(s, period//2).multiply(2).sub(WMA(s, period)), int(np.sqrt(period)))

def EMA(data, n=20):

    emas = data.ewm(span=n,adjust=False).mean()

    return emas

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

def SSL_Custom(df):
    BBMC = HMA(df['HA_close'], 60)
    high_low = df['high'] - df['low']
    high_cp = np.abs(df['high'] - df['close'].shift())
    low_cp = np.abs(df['low'] - df['close'].shift())
    TR = pd.concat([high_low, high_cp, low_cp], axis=1)
    true_range = np.max(TR, axis=1)
    rangema = EMA(true_range, 60)

    upperk = BBMC + rangema * 0.2
    lowerk = BBMC - rangema * 0.2

    color_bar = true_range.copy()
    for i in range(len(color_bar)):
        if(df['HA_close'][i] > upperk[i]):        
            color_bar[i] = 1
        elif(df['HA_close'][i] < lowerk[i]):
            color_bar[i] = -1
        else:
            color_bar[i] = 0

    ExitHigh = HMA(df['HA_high'], 15)
    ExitLow = HMA(df['HA_low'], 15)

    arrow = color_bar.copy()
    lastHlv3 = np.nan

    for i in range(len(ExitHigh)):
        
        if(df['HA_close'][i] > ExitHigh[i]):
            Hlv3 = -1
        elif(df['HA_close'][i] < ExitLow[i]):
            Hlv3 = 1
        else:
            Hlv3 = lastHlv3

        lastHlv3 = Hlv3
        

        if Hlv3 < 0:
            if df['HA_close'][i] > ExitHigh[i] and df['HA_close'][i-1] < ExitHigh[i-1]:
                arrow[i] = 1
            else:
                arrow[i] = 0
        else:
            if ExitLow[i] > df['HA_close'][i] and ExitLow[i-1] < df['HA_close'][i-1]:
                arrow[i] = -1
            else:
                arrow[i] = 0
    

    return BBMC, color_bar, arrow
    


if __name__ == "__main__":

    init()

    api_yaml = get_API()

    binance_api_is_here = False
    binance_secret_is_here = False
    binance_telegram_bot_token_is_here = False
    if "binance_api" in api_yaml:
        binance_api_is_here = True
    if "binance_secret" in api_yaml:
        binance_secret_is_here = True
    if "telegram_bot_token" in api_yaml:
        binance_telegram_bot_token_is_here = True

    if binance_api_is_here == False :
        print(Fore.RED + "[ERREUR] :")
        print(Fore.WHITE + "Il manque -binance_api- dans le fichier api.yaml")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
    if binance_secret_is_here == False :
        print(Fore.RED + "[ERREUR] :")
        print(Fore.WHITE + "Il manque -binance_secret- dans le fichier api.yaml")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
    if binance_telegram_bot_token_is_here == False :
        print(Fore.RED + "[ERREUR] :")
        print(Fore.WHITE + "Il manque -telegram_bot_token- dans le fichier api.yaml")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)



    client_binance = Client(api_yaml['binance_api'], api_yaml['binance_secret'])
    telegram_bot = telepot.Bot(api_yaml['telegram_bot_token'])
    telegram_bot.message_loop(handle_TELEGRAM_COMMAND)
    print(Fore.RED + "[BOT] : ")
    print(Fore.YELLOW + "Commandes du BOT (a envoyer depuis Telegram) :")
    print(Fore.GREEN + "command start :")
    print(Fore.WHITE + "Lance le bot.")
    print(Fore.GREEN + "command info :")
    print(Fore.WHITE + "Donne les paramétrages actuelle du bot.")
    print(Fore.GREEN +"command stop : ")
    print(Fore.WHITE + "Stop le bot.")
    print(Fore.GREEN +"command last_trade_stop : ")
    print(Fore.WHITE + "Termine le dernier trade et arrête le bot,")
    print("si aucun trade n'est en cours, le bot se stop directement.")
    print(Fore.GREEN +"command set_pair -Pair- : ")
    print(Fore.WHITE + "Permet de choisir la pair, ")
    print("une fois que le bot est lancé, ce n'est plus modifiable. (exemple : command set_pair BTCUSDT)")
    print(Fore.GREEN +"command set_trade_amount -Amount- : ")
    print(Fore.WHITE + "Permet de choisir le montant de la mise,")
    print("une fois que le bot est lancé, ce n'est plus modifiable. (exemple : command set_trade_amount 50.5)")
    print(Fore.GREEN +"command set_leverage -Leverage- : ")
    print(Fore.WHITE + "Permet de choisir le multiplicateur de trade, prenez soin de le mettre avant de lancer le bot,")
    print("une fois que le bot est lancé, ce n'est plus modifiable, faite attention de mettre un multiplicateur accepté par votre compte.")
    print("(exemple : command set_leverage 10)")
    print(Fore.GREEN +"command ping : ")
    print(Fore.WHITE + "Si le bot tourne toujours, il renvoit un message 'pong'")

    print(Fore.YELLOW + "Veuillez parametrer la Pair et le montant de la mise depuis Telegram")
    print(Fore.YELLOW + "Puis vous pouver lancer le bot")

    

    while(Telegram_Start_Command_Triggered == False):
        i = 0



    #PARAMETER
    leverage = Telegram_Leverage
    pair = Telegram_Pair


    actualBalance = getUSDTBalanceSTR()
    print("Balance Amount in Futures :")
    print(actualBalance)
    message = "[BOT] : Voici ta balance : " + str(actualBalance) + " USDT"
    telegram_bot.sendMessage(chat_id, message)


    try:
        client_binance.futures_change_leverage(symbol=pair, leverage=int(leverage))
    except Exception as e:
        print(e)
        telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à changer le multiplicateur, peut-être un problème d'api, je m'arrête.")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

    
    precision, pricePrecision = get_precision(client_binance, pair)
    print("Pair and Precision :")
    print(pair + " " + str(precision))


    isLongTake = False
    isShortTake = False
    FirstPoint = False
    lastPricetrade = None
    TradeOrderTime = 0
    TradeOrderTimeSave = 0
    TradeCloseTime = 0
    LogPNL = False

    StopLossPrice = None
    TakeProfitPrice = None

    counterToNotice = 0

    quantityUSDTTrade = Telegram_TradeAmount
    pair = Telegram_Pair

    TradeDateTake = ' '
    TradeDateStop = ' '
    LastDate = ' '

    lastRed = ''
    lastGreen = ''

    lastNumberRed = 0
    lastNumberGreen = 0
    trendCandle = 1

    BoolToPlaceSL_TP = False

    while True :
    
        


        DataCrypto = get_data_frame(client_binance, pair, '2 hours ago UTC', '1m')  

        DataCrypto = HA(DataCrypto)
        BBMC, color_bar, arrow = SSL_Custom(DataCrypto)


        srcCloseElement = len(DataCrypto['close'])-1

        if (DataCrypto['HA_open'][srcCloseElement-1] < DataCrypto['HA_close'][srcCloseElement-1]) and LastDate != DataCrypto['date'][i]:
            if trendCandle == -1:
                lastNumberGreen = 0

            lastGreen = DataCrypto['date'][i]
            lastNumberGreen += 1
            trendCandle = 1


        if (DataCrypto['HA_open'][srcCloseElement-1] > DataCrypto['HA_close'][srcCloseElement-1]) and LastDate != DataCrypto['date'][i]:
            if trendCandle == 1:
                lastNumberRed = 0

            lastRed = DataCrypto['date'][i]
            lastNumberRed += 1
            trendCandle = -1


        if (isLongTake == True or isShortTake == True) and BoolToPlaceSL_TP == False:
            ordersSLTP = client_binance.futures_get_open_orders(symbol=pair)
            if len(ordersSLTP) == 0:
                isLongTake = False
                isShortTake = False
                LogPNL = True


        if TelegramStopSignal == True:
            os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

        if LogPNL == True :
            pnl_history = client_binance.futures_income_history(symbol=pair, incomeType="REALIZED_PNL")
            income = 0.0
            for i in range(len(pnl_history)):
                if int(TradeOrderTime) <= int(pnl_history[i]['time']):
                    income += float(pnl_history[i]['income'])
            print("PNL : ")
            print(income)
            message = "[BOT] : Bop, un trade est terminé. Voici le PNL = " + str(income)
            telegram_bot.sendMessage(chat_id, message)
            if Telegram_LastTradeStop == True:
                    telegram_bot.sendMessage(chat_id, "[BOT] : Le trade est fini, je m'arrête ! ")
                    os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
            LogPNL = False
            quantityUSDTTrade = Telegram_TradeAmount
            pair = Telegram_Pair

        if Telegram_LastTradeStop == True and isLongTake == False and isShortTake == False:
            telegram_bot.sendMessage(chat_id, "[BOT] : Pas de trade en cours, je m'arrête ! ")
            os.execv(sys.executable, [sys.executable, __file__] + sys.argv)
                

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

        if BoolToPlaceSL_TP == True and TradeDateTake == DataCrypto['date'][srcCloseElement-1]:
            if isLongTake == True:
                if DataCrypto['open'][srcCloseElement] >= TakeProfitPrice:
                    while True:
                        try:
                            positionInfo = client_binance.futures_position_information(symbol=pair, timestamp=int(time.time() * 1000))
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer la position du trade, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass

                    while True:
                        try:
                            res = client_binance.futures_create_order(symbol=pair, quantity=float(positionInfo[0].get('positionAmt')), side="SELL", type="MARKET", timestamp=int(time.time() * 1000))
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à close le LONG en cours, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    message = "[BOT][Placement SL/TP LONG] : J'ai fermé le trade, l'open était supérieur au TakeProfit. Open : " + str(DataCrypto['open'][srcCloseElement]) + " TakeProfit: " + str(TakeProfitPrice)
                    telegram_bot.sendMessage(chat_id, message)
                elif DataCrypto['open'][srcCloseElement] <= StopLossPrice:
                    while True:
                        try:
                            positionInfo = client_binance.futures_position_information(symbol=pair, timestamp=int(time.time() * 1000))
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer la position du trade, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass

                    while True:
                        try:
                            res = client_binance.futures_create_order(symbol=pair, quantity=float(positionInfo[0].get('positionAmt')), side="SELL", type="MARKET", timestamp=int(time.time() * 1000))
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à close le LONG en cours, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    message = "[BOT][Placement SL/TP LONG] : J'ai fermé le trade, l'open était inférieur au StopLoss. Open : " + str(DataCrypto['open'][srcCloseElement]) + " StopLoss: " + str(StopLossPrice)
                    telegram_bot.sendMessage(chat_id, message)
                else:

                    while True:
                        try:
                            res = client_binance.futures_create_order(symbol=pair, side='SELL', type='STOP_MARKET', timeInForce='GTE_GTC', quantity=quantityCryptoToBuy, reduceOnly=True, stopPrice=StopLossPrice, workingType='MARK_PRICE')
                            
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à prendre un StopLoss, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    time.sleep(1)
                    while True:
                        try:
                            res = client_binance.futures_create_order(symbol=pair, side='SELL', type='TAKE_PROFIT_MARKET', timeInForce='GTE_GTC', quantity=quantityCryptoToBuy, reduceOnly=True, stopPrice=TakeProfitPrice, workingType='MARK_PRICE')
                            
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à placer un TakeProfit, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    message = "[BOT][Placement SL/TP LONG] : J'ai placé le StopLoss et le TakeProfit. StopLoss : " + str(StopLossPrice) + " TakeProfit: " + str(TakeProfitPrice)
                    telegram_bot.sendMessage(chat_id, message)
                TradeDateStop = DataCrypto['date'][srcCloseElement]
                BoolToPlaceSL_TP = False
            elif isShortTake == True:
                if DataCrypto['open'][srcCloseElement] <= TakeProfitPrice:
                    while True:
                        try:
                            positionInfo = client_binance.futures_position_information(symbol=pair, timestamp=int(time.time() * 1000))
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer la position du trade, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    quan = float(positionInfo[0].get('positionAmt')) * -1.0
                    while True:
                        try:
                            res = client_binance.futures_create_order(symbol=pair, quantity=quan, side="BUY", type="MARKET", timestamp=int(time.time() * 1000))
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à close le SHORT en cours, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    message = "[BOT][Placement SL/TP SHORT] : J'ai fermé le trade, l'open était inférieur au TakeProfit. Open : " + str(DataCrypto['open'][srcCloseElement]) + " TakeProfit: " + str(TakeProfitPrice)
                    telegram_bot.sendMessage(chat_id, message)
                elif DataCrypto['open'][srcCloseElement] >= StopLossPrice:
                    while True:
                        try:
                            positionInfo = client_binance.futures_position_information(symbol=pair, timestamp=int(time.time() * 1000))
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer la position du trade, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    quan = float(positionInfo[0].get('positionAmt')) * -1.0
                    while True:
                        try:
                            res = client_binance.futures_create_order(symbol=pair, quantity=quan, side="BUY", type="MARKET", timestamp=int(time.time() * 1000))
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à close le SHORT en cours, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    message = "[BOT][Placement SL/TP SHORT] : J'ai fermé le trade, l'open était supérieur au StopLoss. Open : " + str(DataCrypto['open'][srcCloseElement]) + " StopLoss: " + str(StopLossPrice)
                    telegram_bot.sendMessage(chat_id, message)
                else:
                    while True:
                        try:
                            res = client_binance.futures_create_order(symbol=pair, side='BUY', type='STOP_MARKET', timeInForce='GTE_GTC', quantity=quantityCryptoToBuy, reduceOnly=True, stopPrice=StopLossPrice, workingType='MARK_PRICE')
                            
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à prendre un StopLoss, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    time.sleep(2)
                    while True:
                        try:
                            res = client_binance.futures_create_order(symbol=pair, side='BUY', type='TAKE_PROFIT_MARKET', timeInForce='GTE_GTC', quantity=quantityCryptoToBuy, reduceOnly=True, stopPrice=TakeProfitPrice, workingType='MARK_PRICE')
                            
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à placer un TakeProfit, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    message = "[BOT][Placement SL/TP SHORT] : J'ai placé le StopLoss et le TakeProfit. StopLoss : " + str(StopLossPrice) + " TakeProfit: " + str(TakeProfitPrice)
                    telegram_bot.sendMessage(chat_id, message)
                TradeDateStop = DataCrypto['date'][srcCloseElement]
                BoolToPlaceSL_TP = False

        
        if isLongTake == False and isShortTake == False and TradeDateStop != DataCrypto['date'][srcCloseElement]:
            print("---------------------")
            print("enter trade Condition -> arrow: " + str(arrow[srcCloseElement]) + " colorbar: " + str(color_bar[srcCloseElement-1]))
            print("lastNumberRed : " + str(lastNumberRed) + " lastNumbergreen : " + str(lastNumberGreen))
            print("lastRed: " + str(lastRed) + " lastGreen: " + str(lastGreen) + " currentDate: " + str(DataCrypto['date'][i]))
            if arrow[srcCloseElement] == 1 and (color_bar[srcCloseElement-1] == 1 or color_bar[srcCloseElement-1] == 0) and lastNumberRed > 0 and lastRed != DataCrypto['date'][i]:
                
                StopLossPrice = DataCrypto['close'][lastRed]
                if float(DataCrypto['open'][srcCloseElement]) - ((float(DataCrypto['open'][srcCloseElement]) * 3.0)/100) <= float(DataCrypto['close'][lastRed]) and StopLossPrice < DataCrypto['open'][srcCloseElement]:

                    StopLossPrice = round_decimals_down(StopLossPrice, int(pricePrecision))
                    TakeProfitPrice =  DataCrypto['open'][srcCloseElement] + (((DataCrypto['low'][lastRed] - DataCrypto['open'][srcCloseElement]) * 1.5) * -1.0)
                    TakeProfitPrice = round_decimals_down(TakeProfitPrice, int(pricePrecision));

                    while True:
                        try:
                            res = client_binance.futures_create_order(symbol=pair, side='BUY', type='MARKET', quantity=quantityCryptoToBuy, reduceOnly=False)
                            TradeOrderTime = res['updateTime']
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à prendre un LONG, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    
                    lastPricetrade = pairPrice
                    message = "[BOT] : J'ai pris un Trade Long. "
                    TradeDateTake = DataCrypto['date'][srcCloseElement]
                    telegram_bot.sendMessage(chat_id, message)
                    print(res)
                    


                    isLongTake = True
                    BoolToPlaceSL_TP = True
                
                
            elif arrow[srcCloseElement] == -1 and (color_bar[srcCloseElement-1] == -1 or color_bar[srcCloseElement-1] == 0) and lastNumberGreen > 0 and lastGreen != DataCrypto['date'][i]:
                
                StopLossPrice = DataCrypto['close'][lastGreen]
                if float(DataCrypto['open'][srcCloseElement]) + ((float(DataCrypto['open'][srcCloseElement]) * 3.0)/100) >= float(DataCrypto['close'][lastGreen]) and StopLossPrice > DataCrypto['open'][srcCloseElement]:

                    StopLossPrice = round_decimals_down(StopLossPrice, int(pricePrecision))
                    TakeProfitPrice =  DataCrypto['open'][srcCloseElement] - (((DataCrypto['high'][lastGreen] - DataCrypto['open'][srcCloseElement]) * 1.5))
                    TakeProfitPrice = round_decimals_down(TakeProfitPrice, int(pricePrecision));
                    while True:
                        try:
                            res = client_binance.futures_create_order(symbol=pair, side='SELL', type='MARKET', quantity=quantityCryptoToBuy, reduceOnly=False)
                            TradeOrderTime = res['updateTime']
                            break
                        except Exception as e:
                            print(e)
                            telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à prendre un LONG, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                            pass
                    
                    lastPricetrade = pairPrice
                    message = "[BOT] : J'ai pris un Trade Short. "
                    TradeDateTake = DataCrypto['date'][srcCloseElement]
                    telegram_bot.sendMessage(chat_id, message)
                    print(res)
                    

                    isShortTake = True
                    BoolToPlaceSL_TP = True
                
        LastDate = DataCrypto['date'][i]
        time.sleep(1)
                    