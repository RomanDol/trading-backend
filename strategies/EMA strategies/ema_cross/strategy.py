import json
import requests
import pandas as pd
from pathlib import Path

# Обязательные параметры платформы
file_name = "EMA_Cross"
symbol = "BTCUSDT"
timeframe = "1m"

# Загружаем параметры из inputs.json
params_path = Path(__file__).parent / "inputs.json"
params = json.loads(params_path.read_text(encoding="utf-8"))

# Преобразуем в словарь {name: value}
param_map = {p["name"]: p.get("value", p["default"]) for p in params}

# Используем параметры
ema_fast = int(param_map["ema_fast"])
ema_slow = int(param_map["ema_slow"])
symbol = param_map.get("symbol", symbol)
timeframe = param_map.get("timeframe", timeframe)

# Загружаем данные с Binance
def fetch_klines(symbol, interval, limit=1000):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    res = requests.get(url)
    data = res.json()
    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "volume", "_", "_", "_", "_", "_", "_"
    ])
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df

df = fetch_klines(symbol, timeframe)

# EMA стратегия
df["ema_fast"] = df["close"].ewm(span=ema_fast).mean()
df["ema_slow"] = df["close"].ewm(span=ema_slow).mean()
df["position"] = (df["ema_fast"] > df["ema_slow"]).astype(int)

# Тестирование
trades = []
equity = []
capital = 100
in_pos = False
entry_price = 0

for i in range(1, len(df)):
    time = df["time"].iloc[i]
    price = df["close"].iloc[i]
    signal = df["position"].iloc[i]

    if not in_pos and signal == 1:
        in_pos = True
        entry_price = price
        trades.append({"date": str(time), "type": "buy", "price": price, "pnl": 0})
    elif in_pos and signal == 0:
        in_pos = False
        pnl = price - entry_price
        capital += pnl
        trades.append({"date": str(time), "type": "sell", "price": price, "pnl": pnl})

    equity.append({"time": str(time), "value": capital})

# Сохраняем результат
Path("data").mkdir(exist_ok=True)
Path("data/equity.json").write_text(json.dumps(equity, indent=2))
Path("data/trades.json").write_text(json.dumps(trades, indent=2))
