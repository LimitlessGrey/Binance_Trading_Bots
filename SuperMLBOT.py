import os
import numpy as np
import pandas as pd
import ccxt
from binance.client import Client
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow import keras
from keras.layers import Dense, LSTM
from keras.models import Sequential
import time

# Set up GPU for training
physical_devices = tf.config.list_physical_devices('GPU')
if len(physical_devices) > 0:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)

# Input your API key and secret key here
api_key = ''
api_secret = ''

client = Client(api_key, api_secret)

def fetch_data(symbol, timeframe, limit):
    exchange = ccxt.binance()
    data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def preprocess_data(df, lookback):
    data = df['close'].values
    scaler = MinMaxScaler()
    data = scaler.fit_transform(data.reshape(-1, 1))

    X, y = [], []
    for i in range(lookback, len(data)):
        X.append(data[i-lookback:i])
        y.append(data[i])
    X, y = np.array(X), np.array(y)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))
    return X, y, scaler

def create_model(lookback):
    model = Sequential()
    model.add(LSTM(units=50, return_sequences=True, input_shape=(lookback, 1)))
    model.add(LSTM(units=50))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model

def round_step(quantity, step_size):
    precision = int(-1 * np.log10(step_size))
    return round(quantity, precision)

symbol = 'BTC/USDT'
timeframe = '15m'
lookback = 15

df = fetch_data(symbol, timeframe, limit=5000)
X, y, scaler = preprocess_data(df, lookback)

model = create_model(lookback)
model.fit(X, y, epochs=10, batch_size=32)

def predict_next_price(model, scaler, last_sequence):
    prediction = model.predict(last_sequence)
    return scaler.inverse_transform(prediction)

def get_last_sequence(symbol, lookback, scaler):
    historical_data = client.get_klines(symbol=symbol.replace('/', ''), interval=Client.KLINE_INTERVAL_1HOUR)
    historical_prices = [float(data[4]) for data in historical_data]
    historical_prices = np.array(historical_prices).reshape(-1, 1)

    scaled_prices = scaler.transform(historical_prices)
    last_sequence = scaled_prices[-lookback:]

    return last_sequence.reshape((1, lookback, 1))

def trade(symbol, model, scaler, lookback):
    while True:
        last_sequence = get_last_sequence(symbol, lookback, scaler)
        predicted_price = predict_next_price(model, scaler, last_sequence)
        current_price_info = client.get_symbol_ticker(symbol=symbol.replace('/', ''))
        current_price = float(current_price_info['price'])

        # Retrieve trading rules and minimum trade quantity from Binance
        trading_rules = client.get_symbol_info(symbol.replace('/', ''))
        min_trade_quantity = float([filter['minQty'] for filter in trading_rules['filters'] if filter['filterType'] == 'LOT_SIZE'][0])
        step_size = float([filter['stepSize'] for filter in trading_rules['filters'] if filter['filterType'] == 'LOT_SIZE'][0])
        min_notional = float([filter['minNotional'] for filter in trading_rules['filters'] if filter['filterType'] == 'MIN_NOTIONAL'][0])

        balance = client.get_asset_balance(asset='USDT')
        available_balance = float(balance['free'])
        trade_quantity_percent = 0.05

        if predicted_price > current_price:
            print('Attempting to Buy:', current_price)
            trade_quantity = max(available_balance * trade_quantity_percent / current_price, min_trade_quantity)
            trade_quantity = round_step(trade_quantity, step_size)

            if available_balance >= trade_quantity * current_price and trade_quantity * current_price >= min_notional:
                order = client.create_order(
                    symbol=symbol.replace('/', ''),
                    side=Client.SIDE_BUY,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=trade_quantity
                )
                print("Order placed:", order)
            else:
                print("Insufficient balance or notional value to place buy order")
        elif predicted_price < current_price:
            print('Attempting to Sell:', current_price)
            balance = client.get_asset_balance(asset='BTC')
            available_balance = float(balance['free'])
            trade_quantity = max(available_balance * trade_quantity_percent, min_trade_quantity)
            trade_quantity = round_step(trade_quantity, step_size)

            if available_balance >= trade_quantity and trade_quantity * current_price >= min_notional:
                order = client.create_order(
                    symbol=symbol.replace('/', ''),
                    side=Client.SIDE_SELL,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=trade_quantity
                )
                print("Order placed:", order)
            else:
                print("Insufficient balance or notional value to place sell order")
        else:
            print('Hold:', current_price)

        # Add a delay before the next trading attempt
        time.sleep(2)  # Sleep for 60 seconds (1 minute)

# Call the trade() function at the end of the script
trade(symbol, model, scaler, lookback)
