# Binance Trading Bots

Five Python bots that trade the BTC/USDT pair on Binance, each with a different
strategy: three based on technical indicators, two on machine learning
price prediction. Each bot is a single script that reads live market data,
computes a signal and places market orders through the Binance API.

This is a learning project: a way to explore market data, indicators and
time-series models on a real exchange. It is not a profitable trading system
and not financial advice.

## The bots

| Script | Strategy | Candles | Decision |
|---|---|---|---|
| `Bollingerbands.py` | Bollinger Bands (20 periods, 2σ), mean reversion | 1 h | Buys below the lower band, sells above the upper band. Checks every minute. |
| `BB_RSI.py` | RSI (14) combined with Bollinger Bands | 1 h | Buys when RSI < 30 **and** price is below the lower band; sells when RSI > 70 **and** price is above the upper band. Checks every 15 minutes. |
| `BinanceBot3.py` | Moving-average crossover (4/8) filtered by RSI | 5 min | Buys on a bullish crossover when RSI < 45, sells when RSI > 55. Risks 3% of the USDT balance per trade and tracks whether it is in a position. |
| `ML_Bot_Binance.py` | Linear regression (scikit-learn) | 1 day | Predicts the next close from the 5-day rolling mean, retrains every 24 h, and buys or sells 50 USDT depending on whether the prediction is above the current price. |
| `SuperMLBOT.py` | LSTM neural network (TensorFlow/Keras) | 15 min | Trains two stacked LSTM layers on the last 5000 closes with a 15-step lookback, predicts the next close, and trades 5% of the balance in that direction. |

All bots round order sizes to the market's precision and check Binance's
minimum order size and minimum notional before placing an order.

## Setup

Python 3 and these packages:

```bash
pip install numpy pandas ccxt python-binance ta scikit-learn tensorflow
```

1. Create an API key on Binance with spot trading enabled, and restrict it to
   the IP address of the machine that runs the bots.
2. Put the key and secret in `api_key` / `api_secret` at the top of the script.
3. Run one bot:

```bash
python BB_RSI.py
```

The bots trade real money as soon as they start. Binance's Spot Testnet is a
safer place to try them; the scripts do not switch to it on their own.

## Known limitations

What I would fix before trusting any of these with real money:

- **No backtesting.** None of the strategies was tested on historical data, so
  there is no evidence any of them is profitable.
- **The ML bots are experimental and do not work reliably.**
  `ML_Bot_Binance.py` splits its data at random, so the model sees the future
  during training, and it only fetches data after the first 24 hours.
  `SuperMLBOT.py` trains on 15-minute candles but predicts from 1-hour candles.
- **API keys live in the source code.** They should come from environment
  variables or a `.env` file that git ignores.
- **No shared code, logging or tests.** Each bot repeats its own exchange and
  order logic and reports through `print`.

## Next steps

- A backtesting module that replays historical candles through each strategy
- A shared exchange and order module used by every bot
- Time-ordered train/test splits and walk-forward validation for the ML models
- Configuration and credentials from environment variables

## Author

- [@Francisco Stigliano](https://github.com/LimitlessGrey)

[![linkedin](https://img.shields.io/badge/linkedin-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/franciscostigliano/)

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
