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

print("BOT_TOKEN =", TOKEN)
print("CHAT_ID   =", CHAT_ID)

# ============================
# CONFIGURAÇÃO DIRETO NO CÓDIGO
# ============================
TICKER = "VALE3.SA"
TARGET_PRICE = 65.00

# ============================
# FUNÇÃO PARA ENVIAR MENSAGEM
# ============================
def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }

    print("➡️ Enviando para Telegram:", payload)

    r = requests.post(url, json=payload)
    print("⬅️ Resposta Telegram:", r.status_code, r.text)

# ============================
# FUNÇÃO PARA CONSULTAR PREÇO
# ============================
def get_price():
    try:
        data = yf.Ticker(TICKER)
        hist = data.history(period="1d", interval="5m")

        if hist.empty:
            print("Histórico vazio!")
            return None

        return float(hist["Close"].iloc[-1])

    except Exception as e:
        print("Erro no yfinance:", e)
        return None

# ============================
# LOOP DE MONITORAMENTO
# ============================
def monitor():
    send_message(f"🚀 Bot iniciado! Monitorando {TICKER} com meta em R$ {TARGET_PRICE:.2f}")

    while True:
        price = get_price()

        if price is None:
            print("Preço None, tentando novamente...")
            time.sleep(20)
            continue

        print(f"{TICKER} → R$ {price}")

        if price >= TARGET_PRICE:
            print("⚠️ ATINGIU O ALVO — ENVIANDO ALERTA!")
            send_message(
                f"🔥 ALVO ATINGIDO!\n"
                f"{TICKER} chegou a R$ {price:.2f}\n"
                f"🎯 Meta: R$ {TARGET_PRICE:.2f}"
            )

        time.sleep(30)

# ============================
# FLASK PARA MANTER O RAILWAY VIVO
# ============================
app = Flask(__name__)

@app.route("/")
def home():
    return f"Bot monitorando {TICKER}..."

if __name__ == "__main__":
    import threading

    t = threading.Thread(target=monitor)
    t.daemon = True
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
