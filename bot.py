import os
import json
import threading
import time
from flask import Flask, request
import requests
import yfinance as yf

# ================================
# CARREGAR VARIÁVEIS DO RAILWAY
# ================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("CHAT_ID")  # ID para enviar os alertas

if not BOT_TOKEN or not ADMIN_CHAT_ID:
    print("❌ ERRO: BOT_TOKEN ou CHAT_ID não configurados no Railway")
    exit()

ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ================================
# BANCO DE DADOS LOCAL (JSON)
# ================================
DATA_FILE = "config.json"

if not os.path.exists(DATA_FILE):
    config = {
        "limites": {"VALE3.SA": 65.0},
        "alert_sent": {}
    }
    with open(DATA_FILE, "w") as f:
        json.dump(config, f, indent=4)
else:
    with open(DATA_FILE, "r") as f:
        config = json.load(f)


def save_config():
    with open(DATA_FILE, "w") as f:
        json.dump(config, f, indent=4)


# ================================
# TELEGRAM – envia mensagens
# ================================
def send_message(chat_id, text):
    try:
        url = f"{BASE_URL}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": text})
        print("Telegram resposta:", r.status_code, r.text)
    except Exception as e:
        print("Erro ao enviar mensagem:", e)


# ================================
# MONITORAMENTO DAS AÇÕES
# ================================
def get_price(ticker):
    """Obtém o último preço de forma estável."""
    try:
        acao = yf.Ticker(ticker)

        # Coleta 1 dia, candles de 1 minuto
        hist = acao.history(period="1d", interval="1m")

        if hist.empty:
            print(f"⚠ Hist vazio para {ticker}")
            return None

        price = float(hist["Close"].iloc[-1])
        return price

    except Exception as e:
        print(f"❌ Erro ao obter preço de {ticker}:", e)
        return None


def monitor_loop():
    print("🔄 Monitoramento iniciado…")
    send_message(ADMIN_CHAT_ID, "🚀 TradeMonitor iniciado e monitorando ações.")

    while True:
        for ticker, limite in config["limites"].items():

            price = get_price(ticker)

            if price is None:
                print(f"Falha ao obter preço de {ticker}")
                continue

            print(f"{ticker} → R$ {price:.2f}")

            alertado = config["alert_sent"].get(ticker, False)

            # Alerta se passar o limite
            if price >= limite and not alertado:
                msg = (
                    f"🚨 ALERTA!\n"
                    f"{ticker} atingiu R$ {price:.2f}\n"
                    f"🎯 Limite configurado: R$ {limite:.2f}"
                )
                send_message(ADMIN_CHAT_ID, msg)

                config["alert_sent"][ticker] = True
                save_config()

        time.sleep(600)  # ajustável


# ================================
# FLASK – WEBHOOK TELEGRAM
# ================================
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    print("📩 Webhook recebido:", update)

    if not update or "message" not in update:
        return "OK"

    chat_id = update["message"]["chat"]["id"]
    text = update["message"].get("text", "")

    # ======================
    # COMANDOS DO BOT
    # ======================

    if text == "/listar":
        msg = "📌 Ações monitoradas:\n\n"
        for t, v in config["limites"].items():
            msg += f"• {t} → limite R$ {v}\n"
        send_message(chat_id, msg)
        return "OK"

    if text.startswith("/configurar"):
        try:
            _, ticker, valor = text.split()
            valor = float(valor)
            ticker = ticker.upper()

            config["limites"][ticker] = valor
            config["alert_sent"][ticker] = False
            save_config()

            send_message(chat_id, f"✔ Limite de {ticker} atualizado para R$ {valor}")
        except:
            send_message(chat_id, "Uso correto:\n/configurar VALE3.SA 67.5")
        return "OK"

    if text.startswith("/adicionar"):
        try:
            _, ticker, valor = text.split()
            valor = float(valor)
            ticker = ticker.upper()

            config["limites"][ticker] = valor
            config["alert_sent"][ticker] = False
            save_config()

            send_message(chat_id, f"✔ {ticker} adicionada com limite R$ {valor}")
        except:
            send_message(chat_id, "Uso:\n/adicionar PETR4.SA 40")
        return "OK"

    if text.startswith("/remover"):
        try:
            _, ticker = text.split()
            ticker = ticker.upper()

            config["limites"].pop(ticker, None)
            config["alert_sent"].pop(ticker, None)
            save_config()

            send_message(chat_id, f"❌ {ticker} removida do monitoramento")
        except:
            send_message(chat_id, "Uso:\n/remover VALE3.SA")
        return "OK"

    if text == "/continuar":
        config["alert_sent"] = {}
        save_config()
        send_message(chat_id, "🔔 Alertas reativados.")
        return "OK"

    send_message(
        chat_id,
        "Comandos disponíveis:\n"
        "/listar\n"
        "/configurar TICKER VALOR\n"
        "/adicionar TICKER VALOR\n"
        "/remover TICKER\n"
        "/continuar"
    )

    return "OK"


@app.route("/")
def home():
    return "TradeMonitor Online"


# ================================
# INICIAR MONITORAMENTO EM THREAD
# ================================
t = threading.Thread(target=monitor_loop)
t.daemon = True
t.start()

# ================================
# MAIN
# ================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

