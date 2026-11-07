"""
Bloco 5 · Contratos & Câmbio — atualiza DATA (cbot_soja/cbot_milho/cotton/
brent/usdbrl/ratio) a partir de duas fontes públicas e gratuitas:

  - CBOT (soja, milho), ICE (algodão) e petróleo Brent: Yahoo Finance, via
    a biblioteca `yfinance` (não-oficial, mas amplamente usada e estável;
    não exige chave de API). Tickers: ZS=F (soja), ZC=F (milho), CT=F
    (algodão), BZ=F (Brent — ICE Brent Crude Futures).
    Brent foi adicionado por ter alta correlação histórica com o preço do
    algodão (fibra sintética/petroquímica compete com o algodão, e custo
    de frete/insumo agrícola também segue o petróleo). Preferido a
    scraping de site (ex.: Investing.com) por ser a mesma fonte já
    validada e estável usada pelos outros 3 contratos deste script.
  - USD/BRL: API oficial do Banco Central do Brasil (SGS — Sistema
    Gerenciador de Séries Temporais), série 1 (dólar de venda, diário).
    https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/N?formato=json
    Pública, sem chave.

*** ATENÇÃO — CONVERSÃO DE UNIDADE (validar isto primeiro) ***
O Yahoo Finance cota ZS=F e ZC=F em CENTAVOS de dólar por bushel (ex.: um
preço mostrado como "1178.25" significa US$ 11,7825/bushel). Este script
já divide por 100 para os dois. O algodão (CT=F) já vem em centavos de
libra-peso (¢/lb), que é a mesma unidade usada no dashboard — não precisa
converter. **Confirmar isso com um valor real antes de confiar no script**,
comparando o resultado com uma cotação conhecida (ex.: Investing.com) no
dia do teste.

IMPORTANTE PARA QUEM FOR VALIDAR (Claude Code):
- `yfinance` precisa estar no requirements.txt (já adicionado).
- O histórico semanal (para o gráfico) é limitado aqui às últimas
  `WEEKS_BACK` semanas via `.history(period=...)`; o restante do
  histórico (2021 em diante) permanece como já estava no arquivo — este
  script só ATUALIZA dados recentes, não reconstrói a série toda.
"""
import sys
import datetime
import requests
import yfinance as yf

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from inject_utils import load_html, save_html, replace_const, extract_const

TICKERS = {
    "cbot_soja": ("ZS=F", 100.0),   # (ticker, divisor de unidade)
    "cbot_milho": ("ZC=F", 100.0),
    "cotton": ("CT=F", 1.0),
    "brent": ("BZ=F", 1.0),         # US$/barril, já na unidade certa
}

BCB_USDBRL_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json"

WEEKS_BACK = 12  # quantas semanas recentes buscar/atualizar por execução


def fetch_weekly_prices(ticker: str, divisor: float):
    """Busca preços semanais (fechamento de sexta-feira) das últimas
    WEEKS_BACK semanas."""
    hist = yf.Ticker(ticker).history(period=f"{WEEKS_BACK * 7}d", interval="1wk")
    out = {}
    for date, row in hist.iterrows():
        d = date.strftime("%Y-%m-%d")
        out[d] = round(float(row["Close"]) / divisor, 4)
    return out


def fetch_usdbrl():
    resp = requests.get(BCB_USDBRL_URL, timeout=30)
    resp.raise_for_status()
    rows = resp.json()  # [{"data": "07/08/2026", "valor": "5.1284"}, ...]
    out = {}
    for r in rows:
        d = datetime.datetime.strptime(r["data"], "%d/%m/%Y").strftime("%Y-%m-%d")
        out[d] = round(float(r["valor"]), 4)
    return out


def nearest_tuesday_map(series_dict, target_dates):
    """A série do dashboard é alinhada em terças-feiras. Os fechamentos
    semanais do yfinance podem cair em outro dia (geralmente sexta) — para
    cada terça-feira alvo, pega o valor mais próximo disponível (olhando
    até 5 dias para trás)."""
    result = {}
    src_dates = sorted(series_dict.keys())
    for td in target_dates:
        target = datetime.datetime.strptime(td, "%Y-%m-%d")
        best = None
        for delta in range(0, 6):
            cand = (target - datetime.timedelta(days=delta)).strftime("%Y-%m-%d")
            if cand in series_dict:
                best = series_dict[cand]
                break
        if best is not None:
            result[td] = best
    return result


def update_html(html_path: str) -> str:
    html = load_html(html_path)
    # occurrence=2: Bloco 5 (preços) é o SEGUNDO `const DATA = ` no arquivo
    # combinado; o Bloco 4 (posições) é o primeiro. Ver README.
    data = extract_const(html, "DATA", occurrence=2)

    existing_dates = [s["date"] for s in data["series"]]
    # gera candidatos de terça-feira para as últimas WEEKS_BACK semanas
    # a partir da última data já presente na série
    last_date = datetime.datetime.strptime(existing_dates[-1], "%Y-%m-%d")
    today = datetime.datetime.utcnow()
    candidate_dates = []
    d = last_date
    while d <= today:
        if d.strftime("%A") == "Tuesday":
            candidate_dates.append(d.strftime("%Y-%m-%d"))
        d += datetime.timedelta(days=1)

    fetched = {}
    for field, (ticker, divisor) in TICKERS.items():
        raw = fetch_weekly_prices(ticker, divisor)
        fetched[field] = nearest_tuesday_map(raw, candidate_dates)

    usdbrl_raw = fetch_usdbrl()
    fetched["usdbrl"] = nearest_tuesday_map(usdbrl_raw, candidate_dates)

    # funde no dict de série existente por data (atualiza se já existir,
    # adiciona se for data nova)
    by_date = {s["date"]: s for s in data["series"]}
    for td in candidate_dates:
        row = by_date.get(td, {"date": td})
        for field in ["cbot_soja", "cbot_milho", "cotton", "brent", "usdbrl"]:
            if td in fetched.get(field, {}):
                row[field] = fetched[field][td]
        by_date[td] = row

    data["series"] = [by_date[d] for d in sorted(by_date.keys())]

    # recalcula stats de cada série (mesma lógica usada no dashboard original)
    def stats(key):
        vals = [s[key] for s in data["series"] if key in s]
        dates = [s["date"] for s in data["series"] if key in s]
        mn, mx = min(vals), max(vals)
        return {
            "avg": round(sum(vals) / len(vals), 3),
            "min": mn, "min_date": dates[vals.index(mn)],
            "max": mx, "max_date": dates[vals.index(mx)],
            "current": vals[-1], "prev": vals[-2],
            "change": round(vals[-1] - vals[-2], 4),
            "current_date": dates[-1],
        }

    data["cbot_soja"] = stats("cbot_soja")
    data["cbot_milho"] = stats("cbot_milho")
    data["cotton"] = stats("cotton")
    data["brent"] = stats("brent")
    data["usdbrl"] = stats("usdbrl")

    ratios = [round(s["cbot_soja"] / s["cbot_milho"], 3) for s in data["series"] if "cbot_soja" in s and "cbot_milho" in s]
    data["ratio"] = {
        "series": ratios,
        "current": ratios[-1],
        "avg": round(sum(ratios) / len(ratios), 3),
    }

    html = replace_const(html, "DATA", data, occurrence=2)
    return html


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../members/mig7lpqvfqpa36k5v3u8rc98/index.html"
    new_html = update_html(path)
    save_html(path, new_html)
    print(f"[precos] DATA (CBOT/ICE/USD-BRL) atualizado em {path}")
