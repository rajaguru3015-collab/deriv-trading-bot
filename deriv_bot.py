# ============================================
# DERIV RSI + EMA AUTO TRADING BOT (SAFE MODE)
# Educational use only
# ============================================

import websocket
import json
import time
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

# ========== USER SETTINGS ==========
API_TOKEN = "PASTE_YOUR_TOKEN_HERE"
SYMBOL = "R_100"
STAKE = 0.35
DURATION = 1
DURATION_UNIT = "m"

RSI_PERIOD = 14
RSI_BUY = 20
RSI_SELL = 80

EMA_FAST = 9
EMA_SLOW = 21

PROFIT_TARGET = 1.0
LOSS_LIMIT = -2.0
# ==================================

balance_start = None
trade_running = False
candles = []

def on_message(ws, message):
    global balance_start, trade_running, candles

    data = json.loads(message)

    # Get balance
    if "balance" in data:
        if balance_start is None:
            balance_start = float(data["balance"]["balance"])
            print("Balance Start:", balance_start)

        current_balance = float(data["balance"]["balance"])
        pnl = current_balance - balance_start

        print("PnL:", round(pnl, 2))

        if pnl >= PROFIT_TARGET or pnl <= LOSS_LIMIT:
            print("TARGET HIT - BOT STOPPED")
            ws.close()

    # Get candles
    if "candles" in data:
        for c in data["candles"]:
            candles.append(c["close"])

        if len(candles) > 50:
            candles = candles[-50:]

        if len(candles) >= EMA_SLOW and not trade_running:
            df = pd.DataFrame(candles, columns=["close"])

            rsi = RSIIndicator(df["close"], RSI_PERIOD).rsi().iloc[-1]
            ema_fast = EMAIndicator(df["close"], EMA_FAST).ema_indicator().iloc[-1]
            ema_slow = EMAIndicator(df["close"], EMA_SLOW).ema_indicator().iloc[-1]

            print("RSI:", round(rsi, 2), "EMA9:", round(ema_fast, 2), "EMA21:", round(ema_slow, 2))

            # BUY CONDITION
            if rsi < RSI_BUY and ema_fast > ema_slow:
                place_trade(ws, "CALL")

            # SELL CONDITION
            elif rsi > RSI_SELL and ema_fast < ema_slow:
                place_trade(ws, "PUT")

    # Trade result
    if "proposal_open_contract" in data:
        if data["proposal_open_contract"]["is_sold"]:
            trade_running = False
            print("Trade Finished")

def place_trade(ws, contract_type):
    global trade_running
    trade_running = True

    print("Placing trade:", contract_type)

    ws.send(json.dumps({
        "buy": 1,
        "price": STAKE,
        "parameters": {
            "amount": STAKE,
            "basis": "stake",
            "contract_type": contract_type,
            "currency": "USD",
            "duration": DURATION,
            "duration_unit": DURATION_UNIT,
            "symbol": SYMBOL
        }
    }))

def on_open(ws):
    ws.send(json.dumps({"authorize": API_TOKEN}))
    time.sleep(1)

    ws.send(json.dumps({"balance": 1, "subscribe": 1}))

    ws.send(json.dumps({
        "ticks_history": SYMBOL,
        "adjust_start_time": 1,
        "count": 50,
        "end": "latest",
        "start": 1,
        "style": "candles",
        "granularity": 60
    }))

    ws.send(json.dumps({
        "ticks": SYMBOL,
        "subscribe": 1
    }))

def on_error(ws, error):
    print("Error:", error)

def on_close(ws):
    print("Connection closed")

if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        "wss://ws.derivws.com/websockets/v3?app_id=1089",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()
