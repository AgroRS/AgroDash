"""
Script temporário de uso único: preenche o histórico completo de Brent
(BZ=F) nas 293 datas já existentes na série do Bloco 5 (2021-01-05 em
diante), já que fetch_prices.py normalmente só atualiza as últimas
WEEKS_BACK semanas — sem isso, "brent" só apareceria pra poucas semanas
recentes em vez de acompanhar todo o histórico do gráfico.

Rodar uma vez (via GitHub Actions, yfinance bloqueado no sandbox local) e
depois apagar este arquivo — daí em diante fetch_prices.py mantém o Brent
atualizado normalmente junto com soja/milho/algodão.
"""
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from inject_utils import load_html, save_html, replace_const, extract_const
from fetch_prices import nearest_tuesday_map, TICKERS


def backfill(html_path: str) -> str:
    html = load_html(html_path)
    data = extract_const(html, "DATA", occurrence=2)

    all_dates = [s["date"] for s in data["series"]]
    ticker, divisor = TICKERS["brent"]

    # fetch_weekly_prices() só busca WEEKS_BACK semanas recentes — pro
    # backfill precisamos do histórico completo, então buscamos direto
    # via yfinance com um período mais longo (cobre desde 2021-01-05).
    import yfinance as yf
    hist = yf.Ticker(ticker).history(period="6y", interval="1wk")
    raw = {}
    for date, row in hist.iterrows():
        d = date.strftime("%Y-%m-%d")
        raw[d] = round(float(row["Close"]) / divisor, 4)

    matched = nearest_tuesday_map(raw, all_dates)
    print(f"[backfill_brent] {len(matched)}/{len(all_dates)} datas encontradas")

    by_date = {s["date"]: s for s in data["series"]}
    for d, v in matched.items():
        by_date[d]["brent"] = v
    data["series"] = [by_date[d] for d in sorted(by_date.keys())]

    vals = [s["brent"] for s in data["series"] if "brent" in s]
    dates = [s["date"] for s in data["series"] if "brent" in s]
    mn, mx = min(vals), max(vals)
    data["brent"] = {
        "avg": round(sum(vals) / len(vals), 3),
        "min": mn, "min_date": dates[vals.index(mn)],
        "max": mx, "max_date": dates[vals.index(mx)],
        "current": vals[-1], "prev": vals[-2],
        "change": round(vals[-1] - vals[-2], 4),
        "current_date": dates[-1],
    }

    html = replace_const(html, "DATA", data, occurrence=2)
    return html


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../members/mig7lpqvfqpa36k5v3u8rc98/index.html"
    new_html = backfill(path)
    save_html(path, new_html)
    print(f"[backfill_brent] Brent (histórico completo) adicionado em {path}")
