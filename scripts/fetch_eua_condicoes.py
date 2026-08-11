"""
Bloco 2 · Condições de lavoura (EUA) — atualiza EUA_CONDITION (Soja/Milho)
e EUA_SUBSOLO a partir do USDA/NASS Quick Stats API.

Fonte oficial, precisa de chave gratuita:
    https://quickstats.nass.usda.gov/api  -> "Request an API Key"

Endpoint: https://quickstats.nass.usda.gov/api/api_GET/

*** ATENÇÃO — ESTE SCRIPT COBRE SÓ A PARTE DOS EUA DO BLOCO 2 ***
Conab (Brasil) e Bolsa de Cereales (Argentina) não têm API pública
conhecida — essas duas partes continuam manuais (planilha/boletim que o
usuário envia). Ver README para o panorama completo do Bloco 2.

Lógica dos dados:
- "% bom + excelente" não vem pronto da API — é a SOMA de duas categorias
  separadas: "PCT EXCELLENT" e "PCT GOOD". Isso é buscado e somado aqui.
- Mesma lógica para umidade de subsolo: "PCT ADEQUATE" + "PCT SURPLUS".
- O dashboard usa rótulos de semana no formato "DD/MM" (dia/mês, PT-BR) —
  a API retorna `week_ending` em formato YYYY-MM-DD; a conversão é feita
  aqui.
- Só a safra corrente (chave "2025/26" no HTML, ajustar para "2026/27"
  quando a safra virar) é atualizada; anos anteriores não mudam.

IMPORTANTE PARA QUEM FOR VALIDAR (Claude Code):
- Conferir se `short_desc` bate exatamente com o que a API espera (os
  valores usados abaixo são os documentados publicamente, mas o texto
  precisa ser exato, incluindo maiúsculas/vírgulas).
- Conferir a MARKETING_YEAR / rótulo de safra corrente — está fixo como
  "2025/26" abaixo; atualizar manualmente quando a safra virar (ou, numa
  segunda iteração, calcular isso a partir da data atual).
"""
import os
import sys
import datetime
import requests

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from inject_utils import load_html, save_html, replace_const, extract_const

NASS_API_KEY = os.environ.get("NASS_API_KEY")
NASS_BASE = "https://quickstats.nass.usda.gov/api/api_GET/"

CURRENT_SEASON_LABEL = "2025/26"  # ajustar quando a safra virar
YEAR = 2026  # ano-safra corrente nos EUA (ajustar junto com o acima)

CONDITION_ITEMS = {
    "Soja": "SOYBEANS",
    "Milho": "CORN",
}


def _nass_get(params: dict):
    params = {**params, "key": NASS_API_KEY, "format": "JSON"}
    resp = requests.get(NASS_BASE, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


def fetch_condition_good_excellent(commodity: str):
    """Retorna {week_label('DD/MM'): pct_bom_mais_excelente} para a safra
    corrente."""
    rows = _nass_get({
        "source_desc": "SURVEY",
        "sector_desc": "CROPS",
        "commodity_desc": commodity,
        "statisticcat_desc": "CONDITION",
        "agg_level_desc": "NATIONAL",
        "freq_desc": "WEEKLY",
        "year": YEAR,
    })
    by_week = {}
    for r in rows:
        desc = r["short_desc"]  # ex: "SOYBEANS - CONDITION, MEASURED IN PCT EXCELLENT"
        if "PCT EXCELLENT" not in desc and "PCT GOOD" not in desc:
            continue
        if "PCT GOOD" in desc and "PCT GOOD," not in desc and "VERY" in desc:
            continue  # evita casar "VERY POOR"/"VERY GOOD" por engano
        week_ending = r["week_ending"]  # "YYYY-MM-DD"
        date = datetime.datetime.strptime(week_ending, "%Y-%m-%d")
        label = date.strftime("%d/%m")
        val = float(r["Value"].replace(",", ""))
        by_week.setdefault(label, 0.0)
        by_week[label] += val
    return {k: round(v, 0) for k, v in by_week.items()}


def fetch_subsoil_adequate_surplus():
    rows = _nass_get({
        "source_desc": "SURVEY",
        "sector_desc": "ENVIRONMENTAL",
        "group_desc": "SOIL",
        "short_desc": "SOIL, MOISTURE, SUBSOIL - PCT ADEQUATE",
        "agg_level_desc": "NATIONAL",
        "freq_desc": "WEEKLY",
        "year": YEAR,
    })
    rows_surplus = _nass_get({
        "source_desc": "SURVEY",
        "sector_desc": "ENVIRONMENTAL",
        "group_desc": "SOIL",
        "short_desc": "SOIL, MOISTURE, SUBSOIL - PCT SURPLUS",
        "agg_level_desc": "NATIONAL",
        "freq_desc": "WEEKLY",
        "year": YEAR,
    })
    by_week = {}
    for r in rows + rows_surplus:
        week_ending = r["week_ending"]
        date = datetime.datetime.strptime(week_ending, "%Y-%m-%d")
        label = date.strftime("%d/%m")
        val = float(r["Value"].replace(",", ""))
        by_week.setdefault(label, 0.0)
        by_week[label] += val
    return {k: round(v, 0) for k, v in by_week.items()}


def merge_into_series(existing_series: list, new_values: dict) -> list:
    """existing_series é uma lista de {"week": "DD/MM", "v": numero_ou_null};
    atualiza só as semanas presentes em new_values, preservando a ordem e
    os rótulos originais."""
    for entry in existing_series:
        if entry["week"] in new_values:
            entry["v"] = new_values[entry["week"]]
    return existing_series


def update_html(html_path: str) -> str:
    if not NASS_API_KEY:
        raise RuntimeError(
            "NASS_API_KEY não encontrada nas variáveis de ambiente. "
            "Cadastre uma chave grátis em https://quickstats.nass.usda.gov/api "
            "e configure como Secret no GitHub (ver README)."
        )

    html = load_html(html_path)

    condition = extract_const(html, "EUA_CONDITION")
    for label, commodity in CONDITION_ITEMS.items():
        new_vals = fetch_condition_good_excellent(commodity)
        condition[label][CURRENT_SEASON_LABEL] = merge_into_series(
            condition[label][CURRENT_SEASON_LABEL], new_vals
        )
    html = replace_const(html, "EUA_CONDITION", condition)

    subsolo = extract_const(html, "EUA_SUBSOLO")
    new_subsolo = fetch_subsoil_adequate_surplus()
    subsolo[CURRENT_SEASON_LABEL] = merge_into_series(
        subsolo[CURRENT_SEASON_LABEL], new_subsolo
    )
    html = replace_const(html, "EUA_SUBSOLO", subsolo)

    return html


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "dashagro_completo.html"
    new_html = update_html(path)
    save_html(path, new_html)
    print(f"[eua_condicoes] EUA_CONDITION e EUA_SUBSOLO atualizados em {path}")
