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


def order_block_finder(df, periods, threshold, usewicks):
    ob_period = periods + 1
    index = 0

    OB_bull = [None] * len(df['close'])
    OB_bull_high = [None] * len(df['close'])
    OB_bull_low = [None] * len(df['close'])
    OB_bull_avg = [None] * len(df['close'])

    OB_bear = [None] * len(df['close'])
    OB_bear_high = [None] * len(df['close'])
    OB_bear_low = [None] * len(df['close'])
    OB_bear_avg = [None] * len(df['close'])

    OB_bull_indic = [None] * len(df['close'])
    OB_bear_indic = [None] * len(df['close'])


    for i in range(len(df['close'])):
        
        if i > 5:
            absmove   = ((abs(df['close'][index-ob_period] - df['close'][index-1]))/df['close'][index-ob_period]) * 100    # Calculate absolute percent move from potential OB to last candle of subsequent candles
            relmove   = absmove >= threshold


            bullishOB = df['close'][index-ob_period] < df['open'][index-ob_period]
            upcandles  = 0
            for x in range(1, periods+1) :
                value = 0
                if df['close'][index-x] > df['open'][index-x] :
                    value = 1
                else:
                    value = 0

                upcandles = upcandles + value

            OB_bull[i]      = bullishOB and (upcandles == (periods)) and relmove          # Identification logic (red OB candle & subsequent green candles)
            #OB_bull_high[i] = OB_bull ? usewicks ? df['high'][index-ob_period] : df['open'][index-ob_period] : np.nan()   # Determine OB upper limit (Open or High depending on input)
            if OB_bull[i] == True:
                if usewicks == True:
                    OB_bull_high[i] = df['high'][index-ob_period]
                else:
                   OB_bull_high[i] = df['open'][index-ob_period]
            else:
                OB_bull_high[i] = np.nan
            #OB_bull_low[i]  = OB_bull ? df['low'][index-ob_period]  : np.nan()                               # Determine OB lower limit (Low)
            if OB_bull[i] == True:
                OB_bull_low[i] = df['low'][index-ob_period]
            else:
                OB_bull_low[i] = np.nan

            OB_bull_avg[i]  = (OB_bull_high[i] + OB_bull_low[i])/2


            bearishOB = df['close'][index-ob_period] > df['open'][index-ob_period]                             # Determine potential Bearish OB candle (green candle)

            downcandles  = 0
            for x in range(1, periods+1) :
                value = 0
                if df['close'][index-x] < df['open'][index-x]:
                    value = 1
                else:
                    value = 0

                downcandles = downcandles + value               # Determine color of subsequent candles (must all be red to identify a valid Bearish OB)

            OB_bear[i]      = bearishOB and (downcandles == (periods)) and relmove        # Identification logic (green OB candle & subsequent green candles)
            #OB_bear_high[i] = OB_bear ? df['high'][index-ob_period] : np.nan()                               # Determine OB upper limit (High)
            if OB_bear[i] == True:
                OB_bear_high[i] = df['high'][index-ob_period]
            else:
                OB_bear_high[i] = np.nan
            #OB_bear_low[i]  = OB_bear ? usewicks ? df['low'][index-ob_period] : df['open'][index-ob_period] : np.nan()    # Determine OB lower limit (Open or Low depending on input)
            if OB_bear[i] == True:
                if usewicks == True:
                    OB_bear_low[i] = df['low'][index-ob_period]
                else:
                    OB_bear_low[i] = df['open'][index-ob_period]
            else:
                OB_bear_low[i] = np.nan

            OB_bear_avg[i]  = (OB_bear_low[i] + OB_bear_high[i])/2                              # Determine OB middle line
            if OB_bull[i] == True:
                OB_bull_indic[i-5] = df['open'][index-5]
            else:
                OB_bull_indic[i] = np.nan

            if OB_bear[i] == True:
                OB_bear_indic[i-5] = df['open'][index-5]
            else:
                OB_bear_indic[i] = np.nan
        else:
            OB_bull_indic[i] = np.nan
            OB_bull[i] = np.nan
            OB_bull_high[i] = np.nan
            OB_bull_low[i] = np.nan
            OB_bull_avg[i] = np.nan

            OB_bear_indic[i] = np.nan
            OB_bear[i] = np.nan
            OB_bear_low[i] = np.nan
            OB_bear_high[i] = np.nan
            OB_bear_avg[i] = np.nan
        index += 1
            

    return {"bull_indic": OB_bull_indic, "bear_indic": OB_bear_indic,"bull":OB_bull, "bull_high":OB_bull_high, "bull_low":OB_bull_low, "bull_avg":OB_bull_avg, "bear":OB_bear, "bear_high":OB_bear_high, "bear_low":OB_bear_low, "bear_avg":OB_bear_avg}


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
            return x['quantityPrecision']

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

    
    precision = get_precision(client_binance, pair)
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
    lastBearPrice = -150.0
    lastBullPrice = -150.0
    
    periods = 5
    threshold = 0.0
    usewicks = False

    counterToNotice = 0

    firstTradeGhost = True

    quantityUSDTTrade = Telegram_TradeAmount
    pair = Telegram_Pair

    while True :
    
        if TelegramStopSignal == True:
            os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

        if LogPNL == True :
            pnl_history = client_binance.futures_income_history(symbol=pair, incomeType="REALIZED_PNL")
            income = 0.0
            for i in range(len(pnl_history)):
                if int(TradeOrderTimeSave) <= int(pnl_history[i]['time']) and int(TradeCloseTime) >= int(pnl_history[i]['time']):
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


        DataCrypto = get_data_frame(client_binance, pair, '6 hours ago UTC', '1m')  

        src = DataCrypto

        order_block = order_block_finder(src, periods, threshold, usewicks)

        np_bull_indic = np.array(order_block['bull_indic']).astype(float)

        np_bear_indic = np.array(order_block['bear_indic']).astype(float)

        np_bull_indic = np_bull_indic[~np.isnan(np_bull_indic)]
        np_bear_indic = np_bear_indic[~np.isnan(np_bear_indic)]





        while True:
            try:
                pairPrice = float(client_binance.futures_symbol_ticker(symbol=pair)['price'])
                break
            except Exception as e:
                print(e)
                telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à récupérer le prix de la pair, si ça se reproduit trop de fois à la suite, veuillez me stopper.")
                pass


        quantityCryptoToBuy = quantityUSDTTrade * leverage / pairPrice
        quantityCryptoToBuy = round_decimals_down(quantityCryptoToBuy, int(precision));


        srcCloseElement = len(src['close'])-1
        bullIndicElement = len(np_bull_indic)-1
        bearIndicElement = len(np_bear_indic)-1

        if np.isnan(np_bull_indic[bullIndicElement]) == False:
            lastBullPrice = np_bull_indic[bullIndicElement]
        if np.isnan(np_bear_indic[bearIndicElement]) == False:
            lastBearPrice = np_bear_indic[bearIndicElement]


        if isLongTake == True :
            if (float(lastPricetrade) - ((float(lastPricetrade) * 0.60)/100) > pairPrice) or float(lastPricetrade) + ((float(lastPricetrade) * 0.20)/100) < pairPrice:
                if firstTradeGhost == False:
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
                    TradeOrderTimeSave = TradeOrderTime
                    TradeCloseTime = res['updateTime']
                    LogPNL = True
                    print(res)
                else:
                    firstTradeGhost = False
                    print('Close Long Ghost Trade :)')
                    telegram_bot.sendMessage(chat_id, "[BOT] : J'ai close le Ghost Trade Long, wouuh ! ")

                isLongTake = False

                

        elif isShortTake == True :
            if (float(lastPricetrade) + ((float(lastPricetrade) * 0.60)/100) < pairPrice) or float(lastPricetrade) - ((float(lastPricetrade) * 0.20)/100) > pairPrice:
                if firstTradeGhost == False:
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
                    TradeOrderTimeSave = TradeOrderTime
                    TradeCloseTime = res['updateTime']
                    LogPNL = True
                    print(res)
                else:
                    firstTradeGhost = False
                    print('Close Short Ghost Trade :)')
                    telegram_bot.sendMessage(chat_id, "[BOT] : J'ai close le Ghost Trade Short, wouuh ! ")

                isShortTake = False
                

        elif isLongTake == False and isShortTake == False:
            if isLongTake == False :
                if lastBearPrice > src['close'][srcCloseElement-1] and lastBearPrice < pairPrice:
                    if firstTradeGhost == False:
                        
                        while True:
                            try:
                                res = client_binance.futures_create_order(symbol=pair, side='BUY', type='MARKET', quantity=quantityCryptoToBuy)
                                TradeOrderTime = res['updateTime']
                                break
                            except Exception as e:
                                print(e)
                                telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à prendre un LONG, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                                pass
                        lastPricetrade = pairPrice
                        telegram_bot.sendMessage(chat_id, "[BOT] : J'ai pris un Trade Long.")
                        print(res)
                    else :
                        print('Take Long Ghost Trade :)')
                        telegram_bot.sendMessage(chat_id, "[BOT] : J'ai pris le Ghost Trade Long, bouh ! ")
                        lastPricetrade = pairPrice


                    isLongTake = True
                    
                    
            if isShortTake == False :
                if lastBullPrice < src['close'][srcCloseElement-1] and lastBullPrice > pairPrice:
                    if firstTradeGhost == False:
                        
                        while True:
                            try:
                                res = client_binance.futures_create_order(symbol=pair, side='SELL', type='MARKET', quantity=quantityCryptoToBuy)
                                TradeOrderTime = res['updateTime']
                                break
                            except Exception as e:
                                print(e)
                                telegram_bot.sendMessage(chat_id, "[BOT] : Erreur : Je n'arrive pas à prendre un SHORT, si ça se reproduit plus de 3 fois à la suite, veuillez me stopper, et allez couper le trade à la main.")
                                pass
                        lastPricetrade = pairPrice
                        telegram_bot.sendMessage(chat_id, "[BOT] : J'ai pris un Trade Short.")
                        print(res)
                    else :
                        print('Take Short Ghost Trade :)')
                        telegram_bot.sendMessage(chat_id, "[BOT] : J'ai pris le Ghost Trade Short, bouh ! ")
                        lastPricetrade = pairPrice

                    isShortTake = True
                

        time.sleep(1)
        # counterToNotice +=1
        # if counterToNotice == 450 :
        #     now = datetime.now()
        #     dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        #     print("I'm Running Now :) ")
        #     print(dt_string)
        #     counterToNotice = 0