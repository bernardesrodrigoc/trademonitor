import os
import json
import threading
import time
import requests
import yfinance as yf
from flask import Flask, request
from datetime import datetime, timedelta, timezone

# ================================
# CONFIGURAÇÕES INICIAIS
# ================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not ADMIN_CHAT_ID:
    print("❌ ERRO: BOT_TOKEN ou CHAT_ID não configurados.")
    # Se estiver rodando localmente sem variáveis de ambiente, comente a linha abaixo
    # exit() 

if ADMIN_CHAT_ID:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
DATA_FILE = "config.json"

# ================================
# PERSISTÊNCIA DE DADOS (JSON)
# ================================
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
# FUNÇÕES DE UTILIDADE (TELEGRAM & BOLSA)
# ================================
def send_message(chat_id, text):
    if not chat_id: return
    try:
        url = f"{BASE_URL}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        print(f"Erro Telegram: {e}")

def get_price(ticker):
    try:
        # Tenta pegar dados rápidos de 1 dia
        acao = yf.Ticker(ticker)
        hist = acao.history(period="1d", interval="1m")
        
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        print(f"Erro yfinance ({ticker}): {e}")
        return None

# ================================
# LÓGICA DE TEMPO E SONO
# ================================
def obter_segundos_ate_proxima_abertura(agora):
    """
    Calcula quantos segundos faltam até as 10:00 do próximo dia útil.
    """
    # Cria um objeto datetime para as 10:00 do dia atual
    target = agora.replace(hour=10, minute=0, second=0, microsecond=0)

    # Se já passou das 10:00 de hoje, o alvo inicial é amanhã
    if agora >= target:
        target += timedelta(days=1)

    # Se o alvo cair em Sábado (5) ou Domingo (6), avança para Segunda
    while target.weekday() > 4:
        target += timedelta(days=1)

    diferenca = (target - agora).total_seconds()
    return max(0, diferenca) # Garante que não retorne negativo

# ================================
# LOOP DE MONITORAMENTO OTIMIZADO
# ================================
def monitor_loop():
    print("🔄 Monitoramento iniciado em background...")
    if ADMIN_CHAT_ID:
        send_message(ADMIN_CHAT_ID, "🚀 TradeMonitor online e otimizado.")

    while True:
        # Forçar Fuso Horário Brasil (UTC-3)
        fuso_brasil = timezone(timedelta(hours=-3))
        agora = datetime.now(fuso_brasil)

        # Regras de horário
        eh_dia_util = agora.weekday() < 5  # 0=Seg, 4=Sex
        mercado_aberto = 10 <= agora.hour < 17

        # --- CENÁRIO 1: MERCADO ABERTO ---
        if eh_dia_util and mercado_aberto:
            print(f"⚡ [{agora.strftime('%H:%M')}] Verificando preços...")
            
            for ticker, limite in config["limites"].items():
                price = get_price(ticker)
                
                if price is None:
                    continue
                
                print(f"   • {ticker}: R$ {price:.2f} (Alvo: {limite})")

                ja_alertou = config["alert_sent"].get(ticker, False)

                if price >= limite and not ja_alertou:
                    msg = f"🚨 ALERTA DE PREÇO!\n\n📈 {ticker} atingiu R$ {price:.2f}\n🎯 Alvo: R$ {limite:.2f}"
                    send_message(ADMIN_CHAT_ID, msg)
                    
                    config["alert_sent"][ticker] = True
                    save_config()

            # Espera 10 minutos (600s) dentro do pregão
            time.sleep(600)

        # --- CENÁRIO 2: MERCADO FECHADO (ECONOMIA MÁXIMA) ---
        else:
            print(f"💤 [{agora.strftime('%H:%M')}] Fora do horário de pregão.")

            # 1. Resetar alertas para o dia seguinte (se já passou das 17h)
            if any(config["alert_sent"].values()):
                print("🧹 Resetando status de alertas para amanhã...")
                config["alert_sent"] = {}
                save_config()

            # 2. Calcular sono profundo
            segundos_para_dormir = obter_segundos_ate_proxima_abertura(agora)
            
            # --- CORREÇÃO AQUI ---
            horas_para_dormir = segundos_para_dormir / 3600  # Variável corrigida

            msg_sleep = f"🌙 Bot entrando em modo de espera por {horas_para_dormir:.1f} horas (até 10:00)."
            print(msg_sleep)
            
            # A thread para AQUI e só acorda na hora exata
            time.sleep(segundos_para_dormir)

# ================================
# SERVIDOR WEB (FLASK)
# ================================
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update or "message" not in update: return "OK"

    chat_id = update["message"]["chat"]["id"]
    text = update["message"].get("text", "").strip()
    
    # Comandos
    if text == "/listar":
        msg = "📌 *Ações Monitoradas:*\n"
        if not config["limites"]: msg += "Nenhuma ação cadastrada."
        for t, v in config["limites"].items():
            status = "✅" if config["alert_sent"].get(t) else "👀"
            msg += f"{status} {t}: R$ {v}\n"
        send_message(chat_id, msg)

    elif text.startswith("/configurar") or text.startswith("/adicionar"):
        try:
            _, ticker, valor = text.split()
            ticker = ticker.upper()
            config["limites"][ticker] = float(valor)
            config["alert_sent"][ticker] = False # Reseta alerta ao editar
            save_config()
            send_message(chat_id, f"💾 {ticker} definido para R$ {valor}")
        except:
            send_message(chat_id, "⚠️ Uso correto: /configurar PETR4.SA 35.50")

    elif text.startswith("/remover"):
        try:
            _, ticker = text.split()
            ticker = ticker.upper()
            if ticker in config["limites"]:
                del config["limites"][ticker]
                if ticker in config["alert_sent"]: del config["alert_sent"][ticker]
                save_config()
                send_message(chat_id, f"🗑 {ticker} removido.")
            else:
                send_message(chat_id, "⚠️ Ação não encontrada.")
        except:
            send_message(chat_id, "⚠️ Uso correto: /remover PETR4.SA")
            
    elif text == "/status":
        fuso = timezone(timedelta(hours=-3))
        agora = datetime.now(fuso).strftime("%d/%m %H:%M")
        send_message(chat_id, f"🤖 Bot Online.\nHorário Servidor: {agora}")

    else:
        if text.startswith("/"):
            send_message(chat_id, "Comandos:\n/listar\n/configurar TICKER VALOR\n/remover TICKER\n/status")

    return "OK"

@app.route("/")
def home():
    return "TradeMonitor Running"

# ================================
# INICIALIZAÇÃO
# ================================
t = threading.Thread(target=monitor_loop)
t.daemon = True
t.start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
