import os
import time
import re
import requests
import yfinance as yf
from flask import Flask

# ----------------------------
# Leitura e validação das ENVs
# ----------------------------
raw_token = os.getenv("BOT_TOKEN")
raw_chat_id = os.getenv("CHAT_ID")

print("RAW BOT_TOKEN repr:", repr(raw_token))
print("RAW CHAT_ID repr:   ", repr(raw_chat_id))

if not raw_token:
    raise SystemExit("ERRO: BOT_TOKEN não definido nas variáveis de ambiente.")

if not raw_chat_id:
    raise SystemExit("ERRO: CHAT_ID não definido nas variáveis de ambiente.")

# Limpa espaços/quebras e caracteres invisíveis
token = raw_token.strip()
chat_id_str = raw_chat_id.strip()

# Remove qualquer caractere que não seja dígito ou sinal de negativo (só por segurança)
chat_id_digits = re.sub(r"[^\d\-]", "", chat_id_str)

print("CLEANED CHAT_ID (digits-only):", repr(chat_id_digits))

# Validar
if chat_id_digits == "":
    raise SystemExit("ERRO: CHAT_ID inválido depois da limpeza. Verifique a variável no Railway.")

# Converter para int quando possível (Telegram aceita tanto string quanto número)
try:
    chat_id = int(chat_id_digits)
except Exception:
    # se não conseguir converter, mantenha como string limpa
    chat_id = chat_id_digits

# ============================
# CONFIGURAÇÃO NO CÓDIGO
# ============================
TICKER = "VALE3.SA"
TARGET_PRICE = 65.00

# ============================
# FUNÇÃO PARA ENVIAR MENSAGEM
# ============================
def send_message(text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    print("➡️ Enviando payload:", payload)
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("⬅️ Resposta Telegram:", r.status_code, r.text)
        return r
    except requests.RequestException as e:
        print("ERRO ao chamar Telegram API:", e)
        return None

# ============================
# FUNÇÃO PARA CONSULTAR PREÇO
# ============================
def get_price():
    try:
        data = yf.Ticker(TICKER)
        hist = data.history(period="1d", interval="5m")
        if hist.empty:
            print("Hist vazio retornado pelo yfinance.")
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        print("Erro no yfinance:", e)
        return None

# ============================
# LOOP DE MONITORAMENTO
# ============================
def monitor():
    print("Iniciando monitoramento...")
    send_message(f"🚀 Bot iniciado! Monitorando {TICKER} com meta em R$ {TARGET_PRICE:.2f}")

    already_alerted = False

    while True:
        price = get_price()
        if price is None:
            print("Preço None — aguardando e tentando novamente.")
            time.sleep(30)
            continue

        print(f"{TICKER} → R$ {price}")

        if price >= TARGET_PRICE and not already_alerted:
            print("⚠️ ATINGIU O ALVO — ENVIANDO ALERTA")
            resp = send_message(
                f"🔥 ALVO ATINGIDO!\n"
                f"{TICKER} chegou a R$ {price:.2f}\n"
                f"🎯 Meta: R$ {TARGET_PRICE:.2f}"
            )
            # Log extra se a API respondeu com erro
            if resp is not None and resp.status_code != 200:
                print("AVISO: Telegram retornou status != 200. Verifique TOKEN / CHAT_ID.")
            already_alerted = True

        time.sleep(30)

# ============================
# FLASK para manter Railway ativo
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
