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

# ============================
# CONFIGURAÇÃO DIRETO NO CÓDIGO
# ============================
TICKER = "VALE3.SA"   # coloque aqui a ação
TARGET_PRICE = 65.00  # coloque aqui o preço-alvo

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
        hist = data.history(period="1d", interval="1m")

        if hist.empty:
            return None

        return float(hist["Close"].iloc[-1])

    except Exception:
        return None


# ============================
# LOOP DE MONITORAMENTO
# ============================
def monitor():
    send_message(f"🚀 Bot iniciado! Monitorando {TICKER} com meta em R$ {TARGET_PRICE:.2f}")

    already_alerted = False

    while True:
        price = get_price()

        if price is None:
            print("Não foi possível obter o preço...")
            time.sleep(30)
            continue

        print(f"{TICKER} → R$ {price}")

        # Condição do alerta
        if price >= TARGET_PRICE and not already_alerted:
            send_message(
                f"🔥 ALVO ATINGIDO!\n"
                f"{TICKER} chegou a R$ {price:.2f}\n"
                f"🎯 Meta configurada: R$ {TARGET_PRICE:.2f}"
            )
            already_alerted = True

        time.sleep(60)  # verifica a cada 1 minuto

# ============================
# FLASK PARA MANTER O RAILWAY VIVO
# ============================
app = Flask(__name__)

@app.route("/")
def home():
    return f"Bot monitorando {TICKER}..."

# ============================
# INICIAR SERVIDOR E MONITOR
# ============================
if __name__ == "__main__":
    import threading

    t = threading.Thread(target=monitor)
    t.daemon = True
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
