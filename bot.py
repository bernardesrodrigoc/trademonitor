import time
import requests
import os
import yfinance as yf

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TARGET_TICKER = os.getenv("TARGET_TICKER")
TARGET_PRICE = float(os.getenv("TARGET_PRICE"))

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message})

while True:
    try:
        ticker = yf.Ticker(TARGET_TICKER)
        price = ticker.history(period="1m")["Close"].iloc[-1]

        print(f"Preço atual {TARGET_TICKER}: {price}")

        if price >= TARGET_PRICE:
            send_telegram(f"⚠️ Alerta! {TARGET_TICKER} atingiu R$ {price:.2f}")
            time.sleep(60)  # evita spam
        else:
            time.sleep(20)

    except Exception as e:
        print("Erro:", e)
        time.sleep(20)
