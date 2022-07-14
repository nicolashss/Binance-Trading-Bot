# ---*--- encoding: UTF-8 ---*---

# pip install tradingview_ta --upgrade
from tradingview_ta import TA_Handler, Interval, Exchange
import tradingview_ta
import time
from colorama import Fore
import sys
import os
import yaml
from binance.client import Client
from binance.exceptions import BinanceAPIException

if os.name == 'nt':
    os.system('cls')

else:
    os.system('clear')

def get_API():

    try:
        yaml_file = open("api.yaml", 'r')

    except:
        print(Fore.RED + "[ERREUR] :")
        print(Fore.WHITE + "Le fichier api.yaml n'existe pas ou n'est pas au bon endroit")
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

    yaml_content = yaml.safe_load(yaml_file)
    return yaml_content

api_yaml = get_API()

client_binance = Client(api_yaml['binance_api'], api_yaml['binance_secret'])

print(">> Version de l'API: " + tradingview_ta.__version__)
print('-------------------------------')

print('\n')

def slowprint(s):
  for c in s + '\n':
    sys.stdout.write(c)
    sys.stdout.flush()
    time.sleep(1./10)

def ui():

    print('Welcome to this software... - By LuX & Doom')

def get_crypto_analyses_signals():

    print('-------------------------------')

    #print(handler.get_analysis().oscillators)
    #print(handler.get_analysis().moving_averages)

    decision = handler.get_analysis().summary['RECOMMENDATION']

    # Output (e, g): {'RECOMMENDATION': 'BUY', 'BUY': 15, 'SELL': 1, 'NEUTRAL': 10}

    print('Détails des indicateurs, et de leurs résultats: ')

    time.sleep(0.4)

    indicateurDetectBuy = handler.get_analysis().summary['BUY']

    print(">> Les indicateurs qui disent de buy sont au nombre de:", str(indicateurDetectBuy))
    time.sleep(0.4)

    indicateurDetectSell = handler.get_analysis().summary['SELL']

    print(">> Les indicateurs qui disent de sell sont au nombre de:", str(indicateurDetectSell))
    time.sleep(0.4)

    indicateurNeutre = handler.get_analysis().summary['NEUTRAL']

    print(">> Les indicateurs qui sont neutre sont au nombre de:", str(indicateurNeutre))
    time.sleep(0.4)

    print('-------------------------------')
    print(f'La décision global des indicateurs disent de: {decision}')
    print('-------------------------------')

def main():

    global handler

    time.sleep(3)

    cryptoCoin = input('>> Coin que tu veux trade: ')
    pair = input('>> Paire avec laquelle tu vas trade: ')

    print('\n')

    handler = TA_Handler(
        symbol=f"{cryptoCoin}{pair}",
        exchange="binance",
        screener="crypto",
        interval=Interval.INTERVAL_5_MINUTES,
    )

    get_crypto_analyses_signals()

    try:
        acc_balance = client_binance.futures_account_balance()

    except Exception as e:

        print(e)
        os.execv(sys.executable, [sys.executable, __file__] + sys.argv)

    for i in range(len(acc_balance)) :
        if acc_balance[i]['asset'] == 'USDT':

            print("Votre balance actuel: " + str(acc_balance[i]['balance'] + " USDT"))

            time.sleep(0.4)

            print('Chargement des libreries...')

            time.sleep(10)

if __name__ == "__main__":
    main()