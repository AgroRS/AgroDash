"""
Bloco 4 · Hedge Funds — atualiza DATA (soja/milho/algodão) a partir do
relatório Legacy Futures Only do CFTC (Commitments of Traders).

Fonte pública, sem necessidade de chave de API (API Socrata do governo dos EUA):
    https://publicreporting.cftc.gov/resource/6dca-aqww.json

Dataset: "Legacy - Futures Only". Categoria usada: Non-Commercial
(NonComm_Positions_Long_All / NonComm_Positions_Short_All) — é a mesma
metodologia usada na planilha original que o usuário forneceu (validada
manualmente conferindo contra as médias históricas da planilha).

IMPORTANTE PARA QUEM FOR VALIDAR (Claude Code):
- Este endpoint aceita filtros via SoQL ($where, $order, $limit) na query
  string. Isso NÃO foi possível testar a partir do ambiente do Claude.ai
  (a ferramenta de fetch usada lá cacheia por URL base, ignorando query
  string) — mas deve funcionar normalmente com `requests` puro, que é o
  que este script usa. Validar isso é o primeiro passo.
- O nome exato da coluna em `market_and_exchange_names` precisa ser
  conferido/ajustado batendo contra uma chamada de teste (ex.:
  "SOYBEANS - CHICAGO BOARD OF TRADE", "CORN - CHICAGO BOARD OF TRADE",
  "COTTON NO. 2 - ICE FUTURES U.S.").
"""
import sys
import statistics
import requests

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from inject_utils import load_html, save_html, replace_const

CFTC_BASE = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"

MARKETS = {
    "soja": "SOYBEANS - CHICAGO BOARD OF TRADE",
    "milho": "CORN - CHICAGO BOARD OF TRADE",
    "algodao": "COTTON NO. 2 - ICE FUTURES U.S.",
}

# quantas semanas manter no histórico — ~10 anos de dados semanais (o
# relatório Legacy COT sai toda semana), com folga
WEEKS_BACK = 530


def fetch_series(market_name: str):
    # IMPORTANTE: $order DESC + $limit é o que garante pegar as WEEKS_BACK
    # semanas MAIS RECENTES. Com ASC, o Socrata retorna as primeiras
    # WEEKS_BACK linhas em ordem cronológica a partir do início da série
    # (1986 pra soja/milho, 2003 pra algodão) — foi exatamente esse bug que
    # fez os 3 gráficos mostrarem histórico dos anos 1980/1990/2000 em vez
    # dos últimos 10 anos. A série é reordenada em ASC de novo logo abaixo,
    # depois de já ter pego o recorte certo.
    params = {
        "$where": f"market_and_exchange_names = '{market_name}'",
        "$select": "report_date_as_yyyy_mm_dd,noncomm_positions_long_all,noncomm_positions_short_all",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": str(WEEKS_BACK),
    }
    resp = requests.get(CFTC_BASE, params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    series = []
    for r in rows:
        date = r["report_date_as_yyyy_mm_dd"][:10]
        long_ = int(float(r["noncomm_positions_long_all"]))
        short_ = int(float(r["noncomm_positions_short_all"]))
        series.append({"date": date, "long": long_, "short": short_, "net": long_ - short_})
    series.sort(key=lambda x: x["date"])
    return series


def compute_stats(series):
    nets = [d["net"] for d in series]
    avg = statistics.mean(nets)
    sd = statistics.pstdev(nets)
    cur, prev = nets[-1], nets[-2]
    sorted_nets = sorted(nets)
    percentile = sum(1 for n in sorted_nets if n <= cur) / len(sorted_nets) * 100
    min_idx = nets.index(min(nets))
    max_idx = nets.index(max(nets))
    return {
        "series": series,
        "avg": round(avg, 0),
        "sd": round(sd, 0),
        "min": min(nets),
        "min_date": series[min_idx]["date"],
        "max": max(nets),
        "max_date": series[max_idx]["date"],
        "current": cur,
        "prev": prev,
        "change": cur - prev,
        "current_date": series[-1]["date"],
        "percentile": round(percentile, 1),
        "zscore": round((cur - avg) / sd, 2) if sd else 0,
    }


def update_html(html_path: str) -> str:
    html = load_html(html_path)
    from inject_utils import extract_const
    # occurrence=1: o Bloco 4 (posições) é o PRIMEIRO `const DATA = ` no arquivo
    # combinado; o Bloco 5 (preços) é o segundo. Ver README.
    full = extract_const(html, "DATA", occurrence=1)
    for key, market_name in MARKETS.items():
        series = fetch_series(market_name)
        full[key] = compute_stats(series)
    html = replace_const(html, "DATA", full, occurrence=1)
    return html


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../members/mig7lpqvfqpa36k5v3u8rc98/index.html"
    new_html = update_html(path)
    save_html(path, new_html)
    print(f"[hedge_funds] DATA (soja/milho/algodao) atualizado em {path}")
