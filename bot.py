import os
import time
import requests
import yfinance as yf
from flask import Flask

# ============================
# VARIÁVEIS DO RAILWAY
# ============================
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TICKER = os.getenv("TICKER")           # ex: "VALE3.SA"
TARGET_PRICE = float(os.getenv("TARGET_PRICE"))  # ex: 65.00

# ============================
# FUNÇÃO PARA ENVIAR MENSAGEM
# ============================
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, json=payload)

# ============================
# FUNÇÃO PARA CONSULTAR PREÇO
# ============================
def get_price():
    try:
        data = yf.Ticker(TICKER)
    except Exception:
        return None

    price = data.history(period="1m")["Close"].iloc[-1]
    return float(price)

# ============================
# LOOP DE MONITORAMENTO
# ============================
def monitor():
    send_message(f"🚀 Bot iniciado! Monitorando {TICKER} com alvo em R$ {TARGET_PRICE:.2f}")

    already_alerted = False

    while True:
        price = get_price()

        if price is None:
            print("Erro ao obter preço... tentando novamente.")
            time.sleep(30)
            continue

        print(f"Preço atual de {TICKER}: {price}")

        # Condição de alerta
        if price >= TARGET_PRICE and not already_alerted:
            send_message(
                f"🔥 ALVO ATINGIDO!\n"
                f"{TICKER} chegou a R$ {price:.2f}\n"
                f"🎯 Meta configurada: R$ {TARGET_PRICE:.2f}"
            )
            already_alerted = True

        time.sleep(60)  # checa 1x por minuto

# ============================
# FLASK PARA MANTER O RAILWAY RODANDO
# ============================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot SwingTrade rodando no Railway!"

# ============================
# START
# ============================
if __name__ == "__main__":
    import threading

    t = threading.Thread(target=monitor)
    t.daemon = True
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
