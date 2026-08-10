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
import sys
import requests

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from inject_utils import load_html, save_html, replace_const, extract_const

NOAA_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

SEASON_TO_MONTH = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}


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
    return html


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "dashagro_completo.html"
    new_html = update_html(path)
    save_html(path, new_html)
    print(f"[clima] ONI_SERIES atualizado em {path}")
