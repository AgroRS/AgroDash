"""
Script de DIAGNÓSTICO temporário — não faz parte da automação normal.
Roda fetch_prices.py contra uma cópia do index.html (não sobrescreve o
arquivo real) e imprime os valores brutos e processados, pra comparar
contra uma fonte conhecida (Google Finance / Investing.com) antes de
confiar no script.

Remover este arquivo (e o workflow scripts-diag.yml) depois de usar.
"""
import json
import shutil
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import fetch_prices
from inject_utils import load_html, extract_const

COPY = "_diag_index_copy.html"


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    shutil.copyfile(src, COPY)

    print("=== valores brutos do yfinance (últimas semanas, ANTES da conversão) ===")
    for field, (ticker, divisor) in fetch_prices.TICKERS.items():
        hist = fetch_prices.yf.Ticker(ticker).history(
            period=f"{fetch_prices.WEEKS_BACK * 7}d", interval="1wk"
        )
        print(f"\n-- {field} ({ticker}), divisor={divisor} --")
        for date, row in hist.tail(4).iterrows():
            close_raw = float(row["Close"])
            print(f"  {date.strftime('%Y-%m-%d')}: Close bruto={close_raw!r} -> convertido={round(close_raw / divisor, 4)}")

    print("\n=== USD/BRL bruto (BCB) ===")
    usdbrl_raw = fetch_prices.fetch_usdbrl()
    for d in sorted(usdbrl_raw.keys())[-4:]:
        print(f"  {d}: {usdbrl_raw[d]}")

    print("\n=== update_html completo (numa cópia) ===")
    new_html = fetch_prices.update_html(COPY)
    data = extract_const(new_html, "DATA", occurrence=2)
    for key in ["cbot_soja", "cbot_milho", "cotton", "usdbrl"]:
        print(f"  {key}: {json.dumps(data[key], ensure_ascii=False)}")
    print(f"  ratio: {json.dumps(data['ratio'], ensure_ascii=False)}")
    print(f"  últimos 3 pontos de series: {json.dumps(data['series'][-3:], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
