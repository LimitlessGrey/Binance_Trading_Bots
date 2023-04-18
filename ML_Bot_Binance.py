import numpy as np
import pandas as pd
import time
import ccxt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

api_key = ''
api_secret = ''

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
})

symbol = 'BTC/USDT'
interval = '1d'
start_date = '3 years ago UTC'
end_date = 'now UTC'

def prepare_data(klines):
    data = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
    data.set_index('timestamp', inplace=True)
    data = data[['close']].astype(float)
    print("Prepared data:", data)  
    return data

def fetch_and_prepare_data(symbol, interval, start_date, end_date):
    start_ts = exchange.parse8601(start_date)
    end_ts = exchange.parse8601(end_date)
    print(f"Parsed start date: {start_ts}, end date: {end_ts}")
    
    klines = exchange.fetch_ohlcv(symbol, interval, start_ts, end_ts)
    print("Fetched klines:", klines)
    if not klines:
        print("No data fetched. Skipping this iteration.")
        return None
    data = prepare_data(klines)
    print("Prepared data:", data)
    return data




def train_model(X_train, y_train):
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model

def place_order(exchange, symbol, side, order_type, quote_balance):
    ticker = exchange.fetch_ticker(symbol)
    price = ticker['ask'] if side == 'BUY' else ticker['bid']
    base_amount = quote_balance / price
    markets = exchange.load_markets()
    market = markets[symbol]
    min_notional = market['limits']['cost']['min']
    symbol_precision = market['precision']['amount']

    required_quote_balance = min_notional / price

    if quote_balance >= required_quote_balance:
        rounded_base_amount = round(base_amount, symbol_precision)
        try:
            order = exchange.create_order(symbol, order_type, side, rounded_base_amount, price)
            print(f"{side} order placed:", order)
        except Exception as e:
            print(f"Error placing {side} order:", e)
    else:
        print(f"Insufficient balance to place {side} order. Minimum required: {required_quote_balance}.")

# Set the frequency at which the bot will fetch new data and make decisions (in seconds)
bot_frequency = 60 * 5  # 5 minutes
model_retraining_frequency = 60 * 60 * 24  # 24 hours
quote_balance = 50  # Adjust the quote balance (USDT) as needed
order_type = 'market'

next_model_retraining = time.time() + model_retraining_frequency
model = LinearRegression()
data = pd.DataFrame()

while True:
    if time.time() > next_model_retraining:
        data = fetch_and_prepare_data(symbol, interval, start_date, end_date)
        if data is None:
            time.sleep(bot_frequency)
            continue

        data['rolling_mean'] = data['close'].shift(1).rolling(window=5).mean()
        data.dropna(inplace=True)

        X = data['rolling_mean'].values.reshape(-1, 1)
        y = data['close'].values.reshape(-1, 1)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        print(f'Mean Squared Error: {mse}')
        next_model_retraining += model_retraining_frequency

    print("Data in the loop:", data)
    if not data.empty:
        latest_rolling_mean = data.iloc[-1]['rolling_mean']
    else:
        print("Data is empty. Skipping this iteration.")
        time.sleep(bot_frequency)
        continue

    if latest_rolling_mean is not None:
        next_price = model.predict(np.array([[latest_rolling_mean]]))[0][0]
    else:
        print("No rolling_mean value. Skipping this iteration.")
        time.sleep(bot_frequency)
        continue

    current_price = exchange.fetch_ticker(symbol)['last']

    if next_price > current_price:
        # Buy BTC
        print("Buying BTC")
        side = 'BUY'
        place_order(exchange, symbol, side, order_type, quote_balance)
    else:
        # Sell BTC
        print("Selling BTC")
        side = 'SELL'
        place_order(exchange, symbol, side, order_type, quote_balance)

    time.sleep(bot_frequency)
    