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
        "limites": {"VALE3.SA": 65.0},   # Limite padrão
        "alert_sent": {},
    }
    with open(DATA_FILE, "w") as f:
        json.dump(config, f)
else:
    with open(DATA_FILE, "r") as f:
        config = json.load(f)


def save_config():
    with open(DATA_FILE, "w") as f:
        json.dump(config, f, indent=4)


# ================================
# TELEGRAM
# ================================
def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})


# ================================
# MONITORAMENTO DAS AÇÕES
# ================================
def monitor_loop():
    while True:
        for ticker, limite in config["limites"].items():
            try:
                acao = yf.Ticker(ticker)
                price = acao.fast_info.get("last_price", None)

                if price is None:
                    print(f"Falha ao obter preço de {ticker}")
                    continue

                print(f"{ticker} → R$ {price}")

                # Verifica se já enviou alerta
                alertado = config["alert_sent"].get(ticker, False)

                # Envia alerta se atingir limite
                if price >= limite and not alertado:
                    msg = f"🚨 ALERTA!\n{ticker} atingiu R$ {price:.2f} (limite: R$ {limite})"
                    send_message(ADMIN_CHAT_ID, msg)

                    config["alert_sent"][ticker] = True
                    save_config()

            except Exception as e:
                print("Erro monitorando:", e)

        time.sleep(10)  # Verifica a cada 10s


# ================================
# WEBHOOK TELEGRAM (para comandos)
# ================================
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    print("Recebido via webhook:", update)

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        # ===============================
        # COMANDOS DO BOT
        # ===============================

        if text == "/continuar":
            config["alert_sent"] = {}
            save_config()
            send_message(chat_id, "Os alertas foram reativados! 🔔")
            return "OK"

        if text == "/listar":
            msg = "📌 Monitorando:\n\n"
            for t, v in config["limites"].items():
                msg += f"• {t} → limite R$ {v}\n"
            send_message(chat_id, msg)
            return "OK"

        if text.startswith("/configurar"):
            try:
                _, ticker, valor = text.split()
                valor = float(valor)
                config["limites"][ticker.upper()] = valor
                config["alert_sent"][ticker.upper()] = False
                save_config()
                send_message(chat_id, f"✔ Limite de {ticker.upper()} atualizado para R$ {valor}")
            except:
                send_message(chat_id, "Uso: /configurar VALE3.SA 67.5")
            return "OK"

        if text.startswith("/adicionar"):
            try:
                _, ticker, valor = text.split()
                valor = float(valor)
                config["limites"][ticker.upper()] = valor
                config["alert_sent"][ticker.upper()] = False
                save_config()
                send_message(chat_id, f"✔ {ticker.upper()} adicionada com limite R$ {valor}")
            except:
                send_message(chat_id, "Uso: /adicionar PETR4.SA 40")
            return "OK"

        if text.startswith("/remover"):
            try:
                _, ticker = text.split()
                ticker = ticker.upper()

                if ticker in config["limites"]:
                    del config["limites"][ticker]
                if ticker in config["alert_sent"]:
                    del config["alert_sent"][ticker]

                save_config()
                send_message(chat_id, f"❌ {ticker} removida do monitoramento.")
            except:
                send_message(chat_id, "Uso: /remover VALE3.SA")
            return "OK"

        send_message(chat_id, "Comandos disponíveis:\n"
                              "/listar\n"
                              "/configurar TICKER VALOR\n"
                              "/adicionar TICKER VALOR\n"
                              "/remover TICKER\n"
                              "/continuar")

    return "OK"


@app.route("/")
def home():
    return "TradeMonitor Online"


# ================================
# INICIAR MONITORAMENTO
# ================================
t = threading.Thread(target=monitor_loop)
t.daemon = True
t.start()


# ================================
# MAIN
# ================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
