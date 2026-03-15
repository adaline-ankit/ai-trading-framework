def compute_basic_features(candles):
    closes = [candle.close for candle in candles]
    if not closes:
        return {}
    return {
        "momentum_5": round(
            (closes[-1] - closes[max(len(closes) - 5, 0)])
            / max(closes[max(len(closes) - 5, 0)], 1.0),
            4,
        ),
        "latest_close": closes[-1],
    }
