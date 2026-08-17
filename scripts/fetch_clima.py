"""
Bloco 1 · Clima — atualiza ONI_SERIES a partir do NOAA CPC.

Fonte pública, sem necessidade de chave de API:
https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt

Formato do arquivo (texto simples, colunas separadas por espaço):
    SEAS  YR   TOTAL  ANOM
    DJF  1950  24.72  -1.53
    JFM  1950  25.17  -1.34
    ...

IMPORTANTE PARA QUEM FOR VALIDAR (Claude Code): este script substitui só
as temporadas com dado REAL publicado (forecast=false). As temporadas
futuras/projetadas (forecast=true) que já existem no HTML são preservadas
como estavam, porque a NOAA não publica previsão em formato de arquivo
baixável — isso normalmente exige atualização manual periódica olhando
https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php
"""
import datetime
import re
import sys
import requests

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from inject_utils import load_html, save_html, replace_const, extract_const

NOAA_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

SEASON_TO_MONTH = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}

MESES_PT = {
    1: "JAN", 2: "FEV", 3: "MAR", 4: "ABR", 5: "MAI", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SET", 10: "OUT", 11: "NOV", 12: "DEZ",
}

BANNER_RE = re.compile(
    r"ATUALIZADO EM <b>[^<]*</b><br>PRÓXIMA DISCUSSÃO CPC/NOAA · [^<]*"
)


def _fmt_data_pt(d: datetime.date) -> str:
    return f"{d.day:02d} {MESES_PT[d.month]} {d.year}"


def _segunda_quinta(ano: int, mes: int) -> datetime.date:
    """A CPC/NOAA publica a discussão ENSO sempre na 2ª quinta-feira do mês."""
    primeiro = datetime.date(ano, mes, 1)
    offset_1a_quinta = (3 - primeiro.weekday()) % 7  # weekday(): quinta = 3
    primeira_quinta = primeiro + datetime.timedelta(days=offset_1a_quinta)
    return primeira_quinta + datetime.timedelta(days=7)


def datas_discussao_enso(hoje: datetime.date):
    """Retorna (última discussão publicada, próxima discussão) com base na
    regra da 2ª quinta-feira do mês — evita depender de atualização manual
    periódica que sempre acaba ficando desatualizada."""
    quinta_deste_mes = _segunda_quinta(hoje.year, hoje.month)
    if hoje >= quinta_deste_mes:
        ultima = quinta_deste_mes
        prox_ano, prox_mes = (hoje.year + 1, 1) if hoje.month == 12 else (hoje.year, hoje.month + 1)
        proxima = _segunda_quinta(prox_ano, prox_mes)
    else:
        proxima = quinta_deste_mes
        ant_ano, ant_mes = (hoje.year - 1, 12) if hoje.month == 1 else (hoje.year, hoje.month - 1)
        ultima = _segunda_quinta(ant_ano, ant_mes)
    return ultima, proxima


def update_banner(html: str, hoje: datetime.date = None) -> str:
    hoje = hoje or datetime.date.today()
    ultima, proxima = datas_discussao_enso(hoje)
    novo_texto = (
        f"ATUALIZADO EM <b>{_fmt_data_pt(ultima)}</b><br>"
        f"PRÓXIMA DISCUSSÃO CPC/NOAA · {_fmt_data_pt(proxima)}"
    )
    return BANNER_RE.sub(novo_texto, html, count=1)


def fetch_oni_real_data():
    resp = requests.get(NOAA_URL, timeout=30)
    resp.raise_for_status()
    lines = resp.text.strip().split("\n")
    header = lines[0].split()  # ['SEAS', 'YR', 'TOTAL', 'ANOM']
    records = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        season, year, total, anom = parts[0], int(parts[1]), float(parts[2]), float(parts[3])
        records.append({
            "year": year,
            "month": SEASON_TO_MONTH[season],
            "season": season,
            "oni": round(anom, 2),
            "forecast": False,
        })
    return records


def update_html(html_path: str) -> str:
    html = load_html(html_path)
    current = extract_const(html, "ONI_SERIES")

    real_data = fetch_oni_real_data()
    real_keys = {(r["year"], r["season"]) for r in real_data}

    # mantém as entradas futuras/projetadas (forecast=true) que já existiam
    # e que a NOAA ainda não "confirmou" com dado real
    kept_forecasts = [
        r for r in current
        if r.get("forecast") and (r["year"], r["season"]) not in real_keys
    ]

    merged = real_data + kept_forecasts
    merged.sort(key=lambda r: (r["year"], r["month"]))

    html = replace_const(html, "ONI_SERIES", merged)
    html = update_banner(html)
    return html


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../members/mig7lpqvfqpa36k5v3u8rc98/index.html"
    new_html = update_html(path)
    save_html(path, new_html)
    print(f"[clima] ONI_SERIES atualizado em {path}")
