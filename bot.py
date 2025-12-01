import os
import time
import re
import json
import requests
import yfinance as yf
from flask import Flask, request

# ----------------------------
# Leitura e validação das ENVs
# ----------------------------
raw_token = os.getenv("BOT_TOKEN")
raw_chat_id = os.getenv("CHAT_ID")

if not raw_token:
    raise SystemExit("ERRO: BOT_TOKEN não definido nas variáveis de ambiente.")

if not raw_chat_id:
    raise SystemExit("ERRO: CHAT_ID não definido nas variáveis de ambiente.")

token = raw_token.strip()
chat_id_str = raw_chat_id.strip()
chat_id_digits = re.sub(r"[^\d\-]", "", chat_id_str)

try:
    chat_id = int(chat_id_digits)
except:
    chat_id = chat_id_digits

# ============================
# CONFIGURAÇÃO NO CÓDIGO
# ============================
TICKER = "VALE3.SA"
TARGET_PRICE = 65.00

STATE_FILE = "state.json"


# ============================
# Funções de estado persistente
# ============================
def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"alerta_liberado": True}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


# ============================
# FUNÇÃO PARA ENVIAR MENSAGEM
# ============================
def send_message(text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass


# ============================
# FUNÇÃO PARA CONSULTAR PREÇO
# ============================
def get_price():
    try:
        data = yf.Ticker(TICKER)
        hist = data.history(period="1d", interval="5m")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except:
        return None


# ============================
# LOOP DE MONITORAMENTO
# ============================
def monitor():
    send_message(f"🚀 Bot iniciado! Monitorando {TICKER} com meta em R$ {TARGET_PRICE:.2f}")

    while True:
        state = load_state()  

        price = get_price()
        if price is None:
            time.sleep(30)
            continue

        print(f"{TICKER} → R$ {price}")

        # ENVIA ALERTA SE O ALVO BATER E O ALERTA ESTIVER LIBERADO
        if price >= TARGET_PRICE and state["alerta_liberado"]:
            send_message(
                f"🔥 ALVO ATINGIDO!\n"
                f"{TICKER} chegou a R$ {price:.2f}\n"
                f"🎯 Meta: R$ {TARGET_PRICE:.2f}\n\n"
                f"Se quiser receber o próximo aviso, envie: /continuar"
            )

            state["alerta_liberado"] = False
            save_state(state)

        time.sleep(30)


# ============================
# FLASK (WEBHOOK TELEGRAM)
# ============================
app = Flask(__name__)

@app.route("/")
def home():
    return f"Bot monitorando {TICKER}..."

@app.route(f"/{token}", methods=["POST"])
def telegram_webhook():
    data = request.json

    if not data or "message" not in data:
        return "ok"

    message = data["message"]
    text = message.get("text", "").strip()

    # Se o usuário enviar /continuar
    if text == "/continuar":
        state = load_state()
        state["alerta_liberado"] = True
        save_state(state)

        send_message("🔔 Novo alerta ativado! Enviarei aviso novamente quando o limite for atingido.")
    
    return "ok"


# ============================
# MAIN
# ============================
if __name__ == "__main__":

    # Inicia o monitoramento em thread separada
    import threading
    t = threading.Thread(target=monitor)
    t.daemon = True
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
