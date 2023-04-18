import ccxt
import numpy as np
import pandas as pd
import time

# Binance API credentials
api_key = ''
api_secret = ''

# Bollinger Bands parameters
symbol = 'BTC/USDT'
timeframe = '1h'
periods = 20
std_dev = 2

# Initialize Binance API
binance = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
})

def get_bollinger_bands(data, periods, std_dev):
    data['MA'] = data['close'].rolling(window=periods).mean()
    data['BB_high'] = data['MA'] + (data['close'].rolling(window=periods).std() * std_dev)
    data['BB_low'] = data['MA'] - (data['close'].rolling(window=periods).std() * std_dev)
    return data

def get_data():
    historical_data = binance.fetch_ohlcv(symbol, timeframe)
    df = pd.DataFrame(historical_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def execute_trade():
    balance = binance.fetch_balance()
    usdt_balance = balance['free']['USDT']
    btc_balance = balance['free']['BTC']

    data = get_data()
    data = get_bollinger_bands(data, periods, std_dev)
    latest = data.iloc[-1]

    if latest['close'] > latest['BB_high'] and btc_balance > 0.001:  # Sell condition
        order = binance.create_market_sell_order(symbol, btc_balance)
        print(f"Selling {btc_balance} BTC at {latest['close']} USDT")

    elif latest['close'] < latest['BB_low'] and usdt_balance > 10:  # Buy condition
        btc_amount = usdt_balance / latest['close']
        order = binance.create_market_buy_order(symbol, btc_amount)
        print(f"Buying {btc_amount} BTC at {latest['close']} USDT")

    else:
        print("No action taken. Waiting for the next opportunity.")

def main():
    while True:
        try:
            execute_trade()
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(e)
            time.sleep(60)  # Retry after 1 minute if an error occurs

if __name__ == '__main__':
    main()
