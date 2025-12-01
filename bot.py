import requests
import time
import os

# Pegos do Railway como variáveis de ambiente
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# 🔧 -- CONFIGURAÇÃO DOS ATIVOS AQUI --
ativos = {
    "VALE3": 65.00
}
# -------------------------------------

def send_message(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def get_price(ticker):
    try:
        url = f"https://brapi.dev/api/quote/{ticker}?range=1d&interval=1d"
        data = requests.get(url).json()
        return float(data["results"][0]["regularMarketPrice"])
    except:
        return None

alertados = set()  # evita alertas repetidos

def main():
    send_message("🤖 Bot iniciado no Railway\nMonitorando VALE3...")

    while True:
        for ticker, preco_compra in ativos.items():

            preco_atual = get_price(ticker)
            if preco_atual is None:
                continue

            variacao = (preco_atual - preco_compra) / preco_compra * 100

            # ALERTA DE +3%
            if variacao >= 3 and ticker not in alertados:
                msg = (
                    f"📈 *ALERTA DE SWING TRADE*\n\n"
                    f"{ticker} atingiu *+{variacao:.2f}%*\n"
                    f"💰 Preço atual: R$ {preco_atual:.2f}\n"
                    f"📌 Preço pago: R$ {preco_compra:.2f}"
                )
                send_message(msg)
                alertados.add(ticker)

        time.sleep(120)  # verifica a cada 2 minutos

if __name__ == "__main__":
    main()
