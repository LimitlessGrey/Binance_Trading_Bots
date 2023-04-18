import ccxt
import time
import numpy as np
import pandas as pd

api_key = ''
api_secret = ''

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
})

symbol = 'BTC/USDT'
timeframe = '1h'

def get_historical_data():
    candles = exchange.fetch_ohlcv(symbol, timeframe)
    np_candles = np.array(candles)
    return np_candles[:, 1:5].astype(float)  # Open, high, low, close prices

def rsi(data, period=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def bollinger_bands(data, period=20, stddev=2):
    sma = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper_band = sma + (stddev * std)
    lower_band = sma - (stddev * std)
    return upper_band, sma, lower_band

def get_rsi_bollinger_strategy_signals(closes, rsi_period=14, bollinger_period=20, bollinger_stddev=2):
    closes = pd.Series(closes)
    rsi_values = rsi(closes, period=rsi_period)
    upper, middle, lower = bollinger_bands(closes, period=bollinger_period, stddev=bollinger_stddev)
    buy_signals = (rsi_values < 30) & (closes < lower)
    sell_signals = (rsi_values > 70) & (closes > upper)
    return buy_signals, sell_signals

def get_symbol_precision():
    markets = exchange.load_markets()
    market = markets[symbol]
    return market['precision']['amount']

symbol_precision = get_symbol_precision()

quote_currency = symbol.split('/')[1]

def place_buy_order(quote_balance):
    ticker = exchange.fetch_ticker(symbol)
    price = ticker['ask']
    base_amount = quote_balance / price
    rounded_base_amount = round(base_amount, symbol_precision)

    markets = exchange.load_markets()
    market = markets[symbol]
    min_notional = market['limits']['cost']['min']

    required_quote_balance = min_notional / price

    if quote_balance >= required_quote_balance:
        try:
            order = exchange.create_market_buy_order(symbol, rounded_base_amount)
            print("Buy order placed:", order)
        except Exception as e:
            print("Error placing buy order:", e)
    else:
        print(f"Insufficient {quote_currency} balance to place buy order. Minimum required: {required_quote_balance}.")

def place_sell_order(base_balance, base_currency):
    ticker = exchange.fetch_ticker(symbol)
    price = ticker['bid']
    
    markets = exchange.load_markets()
    market = markets[symbol]
    min_notional = market['limits']['cost']['min']

    required_base_balance = min_notional / price

    if base_balance >= required_base_balance:
        rounded_base_balance = round(base_balance, symbol_precision)
        try:
            order = exchange.create_market_sell_order(symbol, rounded_base_balance)
            print("Sell order placed:", order)
        except Exception as e:
            print("Error placing sell order:", e)
    else:
        print(f"Insufficient {base_currency} balance to place sell order. Minimum required: {required_base_balance}.")

def main():
    base_currency = symbol.split('/')[0]
    quote_currency = symbol.split('/')[1]

    while True:
        data = get_historical_data()
        closes = data[:, 3]  # Closing prices
        buy_signals, sell_signals = get_rsi_bollinger_strategy_signals(closes)

        rsi_value = rsi(pd.Series(closes)).iloc[-1]
        upper, middle, lower = bollinger_bands(pd.Series(closes))
        print(f"RSI: {rsi_value}, Bollinger Bands (upper, middle, lower): ({upper.iloc[-1]}, {middle.iloc[-1]}, {lower.iloc[-1]})")

        balance = exchange.fetch_balance()
        available_base_balance = float(balance['free'][base_currency])
        available_quote_balance = float(balance['free'][quote_currency])

        print(f"Available {base_currency} balance: {available_base_balance}")
        print(f"Available {quote_currency} balance: {available_quote_balance}")

        if buy_signals.iloc[-1]:
            print("Buy signal")
            if available_quote_balance > 0:
                place_buy_order(available_quote_balance)
            else:
                print(f"Insufficient {quote_currency} balance to place buy order.")
        elif sell_signals.iloc[-1]:
            print("Sell signal")
            if available_base_balance > 0:
                place_sell_order(available_base_balance, base_currency)
            else:
                print(f"Insufficient {base_currency} balance to place sell order.")

        time.sleep(60 * 15)  # Wait for 15 minutes before checking again

if __name__ == '__main__':
    main()