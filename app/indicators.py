import numpy as np
import pandas as pd

def enrich(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    close = x["close"].astype(float)
    high = x["high"].astype(float)
    low = x["low"].astype(float)
    volume = x["volume"].astype(float)

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    x["rsi"] = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    x["macd"] = ema12 - ema26
    x["macd_signal"] = x["macd"].ewm(span=9, adjust=False).mean()
    x["macd_hist"] = x["macd"] - x["macd_signal"]

    x["ema20"] = close.ewm(span=20, adjust=False).mean()
    x["ema50"] = close.ewm(span=50, adjust=False).mean()

    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    x["bb_mid"] = mid
    x["bb_upper"] = mid + 2 * std
    x["bb_lower"] = mid - 2 * std
    x["bb_position"] = (close - x["bb_lower"]) / (x["bb_upper"] - x["bb_lower"])

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    x["atr"] = tr.rolling(14).mean()
    x["atr_pct"] = x["atr"] / close * 100

    x["volume_sma20"] = volume.rolling(20).mean()
    x["volume_ratio"] = volume / x["volume_sma20"]
    x["return_1"] = close.pct_change() * 100
    x["return_5"] = close.pct_change(5) * 100

    x["trend"] = np.select(
        [x["ema20"] > x["ema50"], x["ema20"] < x["ema50"]],
        ["bullish", "bearish"],
        default="neutral"
    )
    return x

def latest_context(df: pd.DataFrame) -> dict:
    row = df.iloc[-1]
    fields = ["close","rsi","macd","macd_signal","macd_hist","ema20","ema50",
              "bb_position","atr","atr_pct","volume_ratio","return_1","return_5"]
    out = {}
    for f in fields:
        v = row.get(f)
        out[f] = None if pd.isna(v) else float(v)
    out["trend"] = str(row.get("trend", "neutral"))
    return out
