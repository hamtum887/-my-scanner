import requests
import pandas as pd
import time
from datetime import datetime, timezone

# ============================================================
# 44 SMA PULLBACK SCANNER
# ============================================================
# BUY:
# - SMA44 rising
# - Price was above SMA44 before pullback
# - Signal candle touches SMA44 by wick/body
# - Bullish candle
# - Candle closes above SMA44
#
# SELL:
# - SMA44 falling
# - Price was below SMA44 before pullback
# - Signal candle touches SMA44 by wick/body
# - Bearish candle
# - Candle closes below SMA44
#
# Only CLOSED candles are checked.
# ============================================================


# ============================================================
# SETTINGS
# ============================================================

BASE_URL = "https://fapi.bitunix.com"

INTERVAL = "1h"

CANDLE_LIMIT = 120

SCAN_INTERVAL_SECONDS = 60

SMA_LENGTH = 44

# ============================================================
# TOP 100 VOLUME COINS
# ============================================================

TOP_COINS = 100

# ============================================================
# TELEGRAM
# ============================================================

TELEGRAM_BOT_TOKEN = "8690661148:AAEYD49z374tUYiXE6uZnu6Hr8Rwaaal7QE"
TELEGRAM_CHAT_ID = "6180132070"


# ============================================================
# DUPLICATE SIGNAL PROTECTION
# ============================================================

sent_signals = set()


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if (
        TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN"
        or TELEGRAM_CHAT_ID == "YOUR_TELEGRAM_CHAT_ID"
    ):
        print("Telegram not configured.")
        return

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:

        response = requests.post(
            url,
            data=payload,
            timeout=10
        )

        if response.status_code == 200:
            print("Telegram sent.")

        else:
            print(
                "Telegram error:",
                response.status_code,
                response.text
            )

    except Exception as e:

        print("Telegram connection error:", e)


# ============================================================
# GET TOP 100 SYMBOLS BY 24H VOLUME
# ============================================================

def get_symbols():

    url = f"{BASE_URL}/api/v1/futures/market/tickers"

    try:

        response = requests.get(
            url,
            timeout=15
        )

        data = response.json()

        if isinstance(data, dict):

            result = data.get("data", data)

        else:

            result = data

        if isinstance(result, dict):

            result = result.get("list", [])

        if not isinstance(result, list):

            print("Unable to read symbol list.")

            return []

        coins = []

        for item in result:

            if not isinstance(item, dict):
                continue

            symbol = (
                item.get("symbol")
                or item.get("s")
            )

            if not symbol:
                continue

            symbol = str(symbol).upper()

            # USDT futures only
            if not symbol.endswith("USDT"):
                continue

            # ------------------------------------------------
            # 24H VOLUME
            # ------------------------------------------------

            volume = (
                item.get("quoteVolume")
                or item.get("quoteVol")
                or item.get("usdtVolume")
                or item.get("volume24h")
                or item.get("volume")
                or item.get("baseVolume")
                or 0
            )

            try:

                volume = float(volume)

            except Exception:

                volume = 0

            coins.append(
                {
                    "symbol": symbol,
                    "volume": volume
                }
            )

        # ----------------------------------------------------
        # Remove duplicate symbols
        # ----------------------------------------------------

        unique_coins = {}

        for coin in coins:

            symbol = coin["symbol"]

            if symbol not in unique_coins:

                unique_coins[symbol] = coin

            else:

                if coin["volume"] > unique_coins[symbol]["volume"]:

                    unique_coins[symbol] = coin

        coins = list(
            unique_coins.values()
        )

        # ----------------------------------------------------
        # Sort by 24H volume
        # Highest volume first
        # ----------------------------------------------------

        coins.sort(
            key=lambda x: x["volume"],
            reverse=True
        )

        # ----------------------------------------------------
        # Top 100
        # ----------------------------------------------------

        top_100 = coins[:TOP_COINS]

        symbols = [
            coin["symbol"]
            for coin in top_100
        ]

        print(
            f"Top {len(symbols)} volume coins loaded."
        )

        return symbols

    except Exception as e:

        print("Symbol API error:", e)

        return []


# ============================================================
# GET CANDLES
# ============================================================

def get_candles(symbol):

    url = (
        f"{BASE_URL}/api/v1/futures/market/kline"
    )

    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "limit": CANDLE_LIMIT
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        data = response.json()

        if isinstance(data, dict):

            result = data.get("data", data)

        else:

            result = data

        if isinstance(result, dict):

            result = result.get("list", [])

        if not isinstance(result, list):

            return None

        if len(result) < SMA_LENGTH + 5:

            return None

        rows = []

        for candle in result:

            # ------------------------------------------------
            # Bitunix candle as dictionary
            # ------------------------------------------------

            if isinstance(candle, dict):

                timestamp = (
                    candle.get("time")
                    or candle.get("timestamp")
                    or candle.get("openTime")
                )

                open_price = (
                    candle.get("open")
                    or candle.get("openPrice")
                )

                high_price = (
                    candle.get("high")
                    or candle.get("highPrice")
                )

                low_price = (
                    candle.get("low")
                    or candle.get("lowPrice")
                )

                close_price = (
                    candle.get("close")
                    or candle.get("closePrice")
                )

                volume = (
                    candle.get("volume")
                    or candle.get("vol")
                    or 0
                )

                rows.append(
                    [
                        timestamp,
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        volume
                    ]
                )

            # ------------------------------------------------
            # Bitunix candle as list
            # ------------------------------------------------

            elif isinstance(candle, list):

                if len(candle) >= 5:

                    rows.append(
                        candle[:6]
                    )

        if not rows:

            return None

        df = pd.DataFrame(
            rows,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
        )

        # ----------------------------------------------------
        # Convert numeric columns
        # ----------------------------------------------------

        for column in [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        df["timestamp"] = pd.to_numeric(
            df["timestamp"],
            errors="coerce"
        )

        df = df.dropna(
            subset=[
                "open",
                "high",
                "low",
                "close"
            ]
        )

        if len(df) < SMA_LENGTH + 5:

            return None

        # ----------------------------------------------------
        # Sort oldest -> newest
        # ----------------------------------------------------

        df = df.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        # ----------------------------------------------------
        # SMA44
        # ----------------------------------------------------

        df["sma44"] = (
            df["close"]
            .rolling(SMA_LENGTH)
            .mean()
        )

        df = df.dropna(
            subset=["sma44"]
        ).reset_index(drop=True)

        if len(df) < 5:

            return None

        return df

    except Exception as e:

        print(
            f"{symbol} candle error:",
            e
        )

        return None


# ============================================================
# CHECK BUY SIGNAL
# ============================================================

def check_buy(df):

    if df is None or len(df) < 4:

        return False

    # --------------------------------------------------------
    # Last CLOSED candle
    # --------------------------------------------------------

    signal_index = len(df) - 2

    previous_index = signal_index - 1

    if previous_index < 1:

        return False

    signal = df.iloc[signal_index]

    previous = df.iloc[previous_index]

    # --------------------------------------------------------
    # SMA44 values
    # --------------------------------------------------------

    sma_now = signal["sma44"]

    sma_previous = previous["sma44"]

    # --------------------------------------------------------
    # SMA44 must be RISING
    # --------------------------------------------------------

    if sma_now <= sma_previous:

        return False

    # --------------------------------------------------------
    # Price was above SMA44 before pullback
    # --------------------------------------------------------

    if previous["close"] <= previous["sma44"]:

        return False

    # --------------------------------------------------------
    # Current candle MUST touch SMA44
    # Wick/body touch
    # --------------------------------------------------------

    if not (
        signal["low"] <= sma_now
        and signal["high"] >= sma_now
    ):

        return False

    # --------------------------------------------------------
    # Bullish candle
    # --------------------------------------------------------

    if signal["close"] <= signal["open"]:

        return False

    # --------------------------------------------------------
    # Candle must close ABOVE SMA44
    # --------------------------------------------------------

    if signal["close"] <= sma_now:

        return False

    return True


# ============================================================
# CHECK SELL SIGNAL
# ============================================================

def check_sell(df):

    if df is None or len(df) < 4:

        return False

    # --------------------------------------------------------
    # Last CLOSED candle
    # --------------------------------------------------------

    signal_index = len(df) - 2

    previous_index = signal_index - 1

    if previous_index < 1:

        return False

    signal = df.iloc[signal_index]

    previous = df.iloc[previous_index]

    # --------------------------------------------------------
    # SMA44 values
    # --------------------------------------------------------

    sma_now = signal["sma44"]

    sma_previous = previous["sma44"]

    # --------------------------------------------------------
    # SMA44 must be FALLING
    # --------------------------------------------------------

    if sma_now >= sma_previous:

        return False

    # --------------------------------------------------------
    # Price was below SMA44 before pullback
    # --------------------------------------------------------

    if previous["close"] >= previous["sma44"]:

        return False

    # --------------------------------------------------------
    # Current candle MUST touch SMA44
    # Wick/body touch
    # --------------------------------------------------------

    if not (
        signal["low"] <= sma_now
        and signal["high"] >= sma_now
    ):

        return False

    # --------------------------------------------------------
    # Bearish candle
    # --------------------------------------------------------

    if signal["close"] >= signal["open"]:

        return False

    # --------------------------------------------------------
    # Candle must close BELOW SMA44
    # --------------------------------------------------------

    if signal["close"] >= sma_now:

        return False

    return True


# ============================================================
# SIGNAL DETAILS
# ============================================================

def get_signal(df):

    if df is None:

        return None

    signal_index = len(df) - 2

    candle = df.iloc[signal_index]

    buy = check_buy(df)

    sell = check_sell(df)

    if buy:

        return {
            "signal": "BUY",
            "candle": candle
        }

    if sell:

        return {
            "signal": "SELL",
            "candle": candle
        }

    return None


# ============================================================
# FORMAT TELEGRAM MESSAGE
# ============================================================

def format_signal(symbol, signal_data):

    signal = signal_data["signal"]

    candle = signal_data["candle"]

    close_price = candle["close"]

    sma44 = candle["sma44"]

    if signal == "BUY":

        emoji = "🟢"

    else:

        emoji = "🔴"

    timestamp = candle["timestamp"]

    try:

        timestamp = float(timestamp)

        if timestamp > 100000000000:

            timestamp = timestamp / 1000

        candle_time = datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc
        ).strftime(
            "%Y-%m-%d %H:%M UTC"
        )

    except Exception:

        candle_time = str(timestamp)

    message = (
        f"{emoji} 44 SMA PULLBACK SIGNAL\n\n"
        f"Coin: {symbol}\n"
        f"Signal: {signal}\n"
        f"Timeframe: {INTERVAL}\n"
        f"Close: {close_price}\n"
        f"SMA44: {sma44}\n"
        f"Candle: {candle_time}\n\n"
        f"✅ SMA44 trend confirmed\n"
        f"✅ Price pulled back to SMA44\n"
        f"✅ SMA44 touched by wick/body\n"
        f"✅ Confirmation candle closed correctly"
    )

    return message


# ============================================================
# MAIN SCAN
# ============================================================

def scan_market():

    print("\n")
    print("=" * 60)
    print("44 SMA PULLBACK SCANNER")
    print("=" * 60)

    print(
        "Timeframe:",
        INTERVAL
    )

    print(
        "Started:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    # --------------------------------------------------------
    # Get TOP 100 by volume
    # --------------------------------------------------------

    symbols = get_symbols()

    if not symbols:

        print(
            "No symbols received from Bitunix."
        )

        return

    print(
        "Coins:",
        len(symbols)
    )

    print("-" * 60)

    signals_found = 0

    for symbol in symbols:

        try:

            df = get_candles(symbol)

            if df is None:

                continue

            signal_data = get_signal(df)

            if signal_data is not None:

                signal = signal_data["signal"]

                candle_timestamp = (
                    signal_data["candle"]["timestamp"]
                )

                # ------------------------------------------------
                # UNIQUE SIGNAL ID
                #
                # Same coin
                # + same BUY/SELL
                # + same candle
                # = same signal
                # ------------------------------------------------

                signal_id = (
                    symbol,
                    signal,
                    candle_timestamp
                )

                # ------------------------------------------------
                # DUPLICATE PROTECTION
                # ------------------------------------------------

                if signal_id in sent_signals:

                    print(
                        f"{symbol}: {signal} already alerted "
                        f"for this candle"
                    )

                    continue

                # ------------------------------------------------
                # NEW SIGNAL
                # ------------------------------------------------

                sent_signals.add(
                    signal_id
                )

                print(
                    f"\n{'=' * 50}"
                )

                print(
                    f"🚨 {signal} SIGNAL"
                )

                print(
                    f"Coin: {symbol}"
                )

                print(
                    f"Close: "
                    f"{signal_data['candle']['close']}"
                )

                print(
                    f"SMA44: "
                    f"{signal_data['candle']['sma44']}"
                )

                print(
                    f"{'=' * 50}"
                )

                message = format_signal(
                    symbol,
                    signal_data
                )

                send_telegram(
                    message
                )

                signals_found += 1

            else:

                print(
                    f"{symbol}: No signal"
                )

        except Exception as e:

            print(
                f"{symbol}: Scan error:",
                e
            )

    print("-" * 60)

    print(
        "Signals found:",
        signals_found
    )

    print(
        "Scan completed:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print("=" * 60)


# ============================================================
# START SCANNER
# ============================================================

def main():

    print(
        "\n"
        "==============================================\n"
        "   44 SMA PULLBACK SCANNER v1.0\n"
        "==============================================\n"
    )

    print(
        "Scanner starting..."
    )

    # --------------------------------------------------------
    # Continuous scanner
    # --------------------------------------------------------

    while True:

        try:

            scan_market()

        except Exception as e:

            print(
                "Main scanner error:",
                e
            )

        print(
            f"\nNext scan in {SCAN_INTERVAL_SECONDS} seconds..."
        )

        time.sleep(
            SCAN_INTERVAL_SECONDS
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()