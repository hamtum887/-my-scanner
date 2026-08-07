import requests
import time
import pandas as pd
BOT_TOKEN = "8690661148:AAFhGhkuTYJoz59BLuAoDNId7nzte2Xa00w"
CHAT_ID = "6180132070"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    response = requests.post(url, data=data)
    print(response.text)
send_telegram("✅ Telegram Test Successful")
from ta.trend import EMAIndicator, SMAIndicator
market_url = "https://fapi.bitunix.com/api/v1/futures/market/tickers"

response = requests.get(market_url)
market_data = response.json()

symbols = []

for coin in market_data["data"]:
    symbol = coin["symbol"]

    coin["gain"] = (
        (float(coin["lastPrice"]) - float(coin["open"]))
        / float(coin["open"])
    ) * 100

market_data["data"].sort(
    key=lambda x: x["gain"],
    reverse=True
)

for coin in market_data["data"]:
    symbol = coin["symbol"]

    if symbol.endswith("USDT"):
        symbols.append(symbol)

symbols = symbols[:50]
fixed_symbols = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT"
]

symbols = fixed_symbols + symbols
symbols = list(dict.fromkeys(symbols))

print("Total Coins :", len(symbols))
print(symbols)




for symbol in symbols:
    # print(f"\n====================")
    # print(f"Scanning : {symbol}")
    # print("====================")

    url = f"https://fapi.bitunix.com/api/v1/futures/market/kline?symbol={symbol}&interval=15m&limit=100"

    response = requests.get(url)
    data = response.json()

    if data["code"] != 0:
        print(f"Error fetching {symbol}")
        continue



    candles = data["data"]

    df = pd.DataFrame(candles)
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["open"] = df["open"].astype(float)

    df["EMA21"] = EMAIndicator(close=df["close"], window=21).ema_indicator()
    df["SMA44"] = SMAIndicator(close=df["close"], window=44).sma_indicator()

   # print(df[["close", "EMA21", "SMA44"]].tail(10))

    if df["EMA21"].iloc[-1] > df["EMA21"].iloc[-2]:
        print("\nEMA 21 : Rising")
    else:
        print("\nEMA 21 : Falling")

    if df["SMA44"].iloc[-1] > df["SMA44"].iloc[-2]:
        print("SMA 44 : Rising")
    else:
        print("SMA 44 : Falling")
    df["Bullish"] = df["close"] > df["EMA21"]
    df["Bearish"] = df["close"] < df["EMA21"]

    last = df.iloc[-1]
    prev1 = df.iloc[-2]
    prev2 = df.iloc[-3]
    prev3 = df.iloc[-4]
    prev4 = df.iloc[-5]
    prev5 = df.iloc[-6]
    lookback = 30
    recent = df.tail(lookback)
    trend_start = None

    for i in range(len(recent)):
        row = recent.iloc[i]

        if (
            row["close"] > row["EMA21"] and
            row["close"] > row["SMA44"]
        ):
            trend_start = i
            break
        trend_valid = False
    trend_valid = False
    trend_broken = False
    pullback_started = False
    pullback_index = None
    pullback_price = None
    if trend_start is not None:
        trend_valid = True
    if trend_valid and not trend_broken:
        for i in range(trend_start, len(recent)):
            row = recent.iloc[i]

            if (
        row["low"] <= row["EMA21"] or
        row["low"] <= row["SMA44"]
    ):
                pullback_started = True
                pullback_index = i
                pullback_price = row["close"]
                break

    if trend_valid:
        for i in range(trend_start, len(recent)):
            row = recent.iloc[i]

            if row["close"] < row["SMA44"]:
                trend_broken = True
                break
            
    pullback_confirmed = False
    recovery_candle = False

    if pullback_started and pullback_index is not None:
        for i in range(pullback_index + 1, len(recent)):
            row = recent.iloc[i]

            if row["close"] > row["EMA21"] and row["close"] > row["SMA44"]:
                recovery_candle = True
                break


    if pullback_started:
        if (
            last["low"] <= last["EMA21"] or
            last["low"] <= last["SMA44"]
        ) and (
            last["close"] > last["EMA21"] and
            last["close"] > last["SMA44"]
        ):
            pullback_confirmed = True

    print("\n----------------")
    print("Current Close :", last["close"])
    print("EMA21 :", last["EMA21"])
    print("SMA44 :", last["SMA44"])

    if last["Bullish"]:
        print("Price is ABOVE EMA21")

    if last["Bearish"]:
        print("Price is BELOW EMA21")
    # EMA21 Touch
    ema_touch = last["low"] <= last["EMA21"] <= last["high"]

    # SMA44 Touch
    sma_touch = last["low"] <= last["SMA44"] <= last["high"]
    pullback_ma = "None"

    if ema_touch:
        pullback_ma = "EMA21"

    elif sma_touch:
        pullback_ma = "SMA44"
    print("\nTouch Status")
    print("Pullback MA :", pullback_ma)
    if ema_touch:
        print("EMA21 Touched")
    else:
        print("EMA21 Not Touched")

    if sma_touch:
        print("SMA44 Touched")
    else:
        print("SMA44 Not Touched")

    print("\nPullback Check")
    ema_rising = df["EMA21"].iloc[-1] > df["EMA21"].iloc[-2]
    sma_rising = df["SMA44"].iloc[-1] > df["SMA44"].iloc[-2]

    ema_falling = df["EMA21"].iloc[-1] < df["EMA21"].iloc[-2]
    sma_falling = df["SMA44"].iloc[-1] < df["SMA44"].iloc[-2]
    ema_slope = abs(df["EMA21"].iloc[-1] - df["EMA21"].iloc[-2])
    sma_slope = abs(df["SMA44"].iloc[-1] - df["SMA44"].iloc[-2])

    print("EMA Slope :", ema_slope)
    print("SMA Slope :", sma_slope)
    strong_trend = (
        ema_slope > 20 and
        sma_slope > 10
    )

    print("Strong Trend :", strong_trend)
    sideways = (
        ema_slope < 5 and
        sma_slope < 5 and
        abs(last["close"] - last["EMA21"]) < 100 and
        abs(last["close"] - last["SMA44"]) < 100
    )

    print("Sideways :", sideways)
    trend_buy = (
        trend_valid and
        not trend_broken and
        ema_rising and
        sma_rising and
        last["close"] > last["EMA21"] and
        last["close"] > last["SMA44"]
    )

    trend_sell = (
        trend_valid and
        not trend_broken and
        ema_falling and
        sma_falling and
        last["close"] < last["EMA21"] and
        last["close"] < last["SMA44"]
    )

    pullback_recovered = (
        last["close"] > last["EMA21"] or
        last["close"] > last["SMA44"]
    )

    pullback_buy = (
        trend_buy and
        pullback_started and
        pullback_confirmed and
        pullback_recovered and
        recovery_candle
    )

    pullback_sell = (
        trend_sell and
        pullback_started and
        pullback_confirmed and
        recovery_candle and
        (
            last["close"] < last["EMA21"] or
            last["close"] < last["SMA44"]
        )
    )

    if pullback_buy:
        print("BUY Pullback Found")
    if pullback_sell:
        print("SELL Pullback Found") 
        print("\nConfirmation Check")
    bull_body = last["close"] - last["open"]
    bear_body = last["open"] - last["close"]

    candle_range = last["high"] - last["low"]
    body_ratio = bull_body / candle_range if candle_range > 0 else 0
    strong_bounce = (
        (last["close"] - last["low"]) >
        ((last["high"] - last["low"]) * 0.5)
    )
    bullish_confirmation = (
        last["close"] > last["open"] and
        last["close"] > prev1["high"] and
        body_ratio >= 0.5
    )

    bearish_confirmation = (
        last["close"] < last["open"] and
        last["close"] < prev1["low"] and
        (bear_body / candle_range if candle_range > 0 else 0) >= 0.5
    )

    if bullish_confirmation:
        print("Bullish Confirmation")

    if bearish_confirmation:
        print("Bearish Confirmation")

    final_buy = (
        pullback_buy and
        bullish_confirmation
    )

    final_sell = (
        pullback_sell and
        bearish_confirmation
    )

    if final_buy:
        print("✅ FINAL BUY SIGNAL")

    if final_sell:
        print("🔴 FINAL SELL SIGNAL")


    buy_signal = (
        ema_rising and
        sma_rising and
        pullback_buy and
        bullish_confirmation and
        strong_trend and
        strong_bounce and
        not sideways
    )

    sell_signal = (
        ema_falling and
        sma_falling and
        pullback_sell and
        bearish_confirmation and
        strong_trend and
        strong_bounce and
        not sideways
)

if buy_signal:
    print(f"🟢 BUY SIGNAL : {symbol}")
    send_telegram(f"🟢 BUY SIGNAL : {symbol}")

elif sell_signal:
    print(f"🔴 SELL SIGNAL : {symbol}")
    send_telegram(f"🔴 SELL SIGNAL : {symbol}")
    time.sleep(0.2)

 #print("\nDebug Status")

 #print("EMA Rising :", ema_rising)
 #print("SMA Rising :", sma_rising)
 #print("EMA Falling :", ema_falling)
 #print("SMA Falling :", sma_falling)

 #print("EMA Touch :", ema_touch)
 #print("SMA Touch :", sma_touch)

 #print("Pullback Buy :", pullback_buy)
 #print("Pullback Sell :", pullback_sell)

 #print("Bullish Confirmation :", bullish_confirmation)
 #print("Bearish Confirmation :", bearish_confirmation)
 #print("Previous Close 1 :", prev1["close"])
 #print("Previous Close 2 :", prev2["close"])
 #print("Previous Close 3 :", prev3["close"])
 #print("Previous Close 4 :", prev4["close"])