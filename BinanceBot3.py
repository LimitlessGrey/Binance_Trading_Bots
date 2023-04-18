import ccxt
import numpy as np
import pandas as pd
import time
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from math import ceil

api_key = ''
secret_key = ''

symbol = 'BTC/USDT'
timeframe = '5m'
short_ma = 4
long_ma = 8
rsi_period = 14
rsi_buy_threshold = 45
rsi_sell_threshold = 55
exposure = 0.03

binance = ccxt.binance({
    'apiKey': api_key,
    'secret': secret_key,
    'enableRateLimit': True,
})

# Load markets
binance.load_markets()
market_data = binance.market(symbol)
min_order_size = market_data['limits']['amount']['min']
min_notional = market_data['limits']['cost']['min']

def round_up(value, decimals):
    multiplier = 10 ** decimals
    return ceil(value * multiplier) / multiplier

def fetch_ohlcv_data(symbol, timeframe, limit):
    return binance.fetch_ohlcv(symbol, timeframe, limit=limit)

def create_market_buy_order(symbol, quote_amount):
    return binance.create_market_buy_order(symbol, None, quote_amount)

def create_market_sell_order(symbol, base_amount):
    return binance.create_market_sell_order(symbol, base_amount)

def fetch_balance(coin):
    balance = binance.fetch_balance()
    return float(balance['total'][coin])

def moving_average_cross(prices, short_ma, long_ma):
    short_mavg = np.convolve(prices, np.ones(short_ma), 'valid') / short_ma
    long_mavg = np.convolve(prices, np.ones(long_ma), 'valid') / long_ma

    # Print the latest values of the moving averages
    print(f'Short-term MA ({short_ma} periods): {short_mavg[-1]}')
    print(f'Long-term MA ({long_ma} periods): {long_mavg[-1]}')

    # Calculate the difference between the latest moving averages
    ma_difference = short_mavg[-1] - long_mavg[-1]
    print(f'Moving average difference: {ma_difference}')

    return short_mavg[-1] > long_mavg[-1] and short_mavg[-2] <= long_mavg[-2]

def calculate_rsi(close_prices, period):
    close_prices_series = pd.Series(close_prices)
    rsi = RSIIndicator(close_prices_series, period)
    return rsi.rsi().iloc[-1]

def main():
    in_position = True

    markets = binance.load_markets()
    min_order_size = markets[symbol]['limits']['amount']['min']

    while True:
        try:
            ohlcv_data = fetch_ohlcv_data(symbol, timeframe, max(long_ma, rsi_period) + 1)
            closing_prices = np.array([x[4] for x in ohlcv_data])

            ma_cross_buy = moving_average_cross(closing_prices, short_ma, long_ma)

            rsi = calculate_rsi(closing_prices, rsi_period)
            print(f'RSI: {rsi}')
            rsi_buy = rsi < rsi_buy_threshold
            rsi_sell = rsi > rsi_sell_threshold
            print(f'RSI Buy: {rsi_buy}, RSI Sell: {rsi_sell}')

            if ma_cross_buy:
                print('Moving Average Cross BUY signal')
                if rsi_buy:
                    print('RSI BUY signal')
                    if not in_position:
                        quote_currency = 'USDT'
                        quote_balance = fetch_balance(quote_currency)
                        order_amount = quote_balance * exposure
                        if order_amount * closing_prices[-1] < min_notional:
                            order_amount = round_up(min_notional / closing_prices[-1], market_data['precision']['amount'])

                        if order_amount > 0:
                            order_amount = order_amount / closing_prices[-1]
                            print(f'Executing BUY order for {order_amount} {quote_currency}')
                            amount_precision = market_data['precision']['amount']
                            formatted_order_amount = f"{order_amount:.{amount_precision}f}"
                            order = create_market_buy_order(symbol, formatted_order_amount)  # Format order_amount as a string with proper precision
                            print(f'Buy order executed: {order}')
                            in_position = True

                    else:
                        print('Already in position, skipping BUY order')

            elif rsi_sell:
                print('SELL signal')
                if in_position:
                    base_currency = 'BTC'
                    base_balance = fetch_balance(base_currency)
                    if base_balance * closing_prices[-1] < min_notional:
                        base_balance = round_up(min_notional / closing_prices[-1], market_data['precision']['amount'])
                    if base_balance >= min_order_size:
                        print(f'Executing SELL order for {base_balance} {base_currency}')
                        order = create_market_sell_order(symbol, base_balance)
                        print(f'Sell order executed: {order}')
                        in_position = False
                else:
                    print('No position to sell, skipping SELL order')

            time.sleep(binance.rateLimit / 1000)
            #print('Waiting for the next iteration...\n')

        except Exception as e:
            print(f'Error: {e}')
            time.sleep(60)

if __name__ == '__main__':
    main()
