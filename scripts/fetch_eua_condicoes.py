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
  a API retorna `week_ending` em formato YYYY-MM-DD (sempre um domingo).
  IMPORTANTE: o dashboard rotula cada semana pela SEXTA-FEIRA seguinte
  (domingo + 5 dias), não pelo próprio domingo — ver `_week_label()` e
  `DASHBOARD_LABEL_OFFSET_DAYS`. Confirmado comparando os rótulos já
  existentes no HTML contra as datas reais da API: sem esse ajuste,
  `merge_into_series` nunca encontra a semana correspondente e a
  atualização vira um no-op silencioso (roda sem erro, mas não muda
  nada — foi exatamente o que aconteceu na primeira validação real).
- Só a safra corrente (chave "2025/26" no HTML, ajustar para "2026/27"
  quando a safra virar) é atualizada; anos anteriores não mudam.

Validado com chamada real (via GitHub Actions) em 2026-08-11:
- A consulta de condição (soja/milho) funcionou de primeira — os
  `short_desc` "SOYBEANS - CONDITION, MEASURED IN PCT EXCELLENT" etc.
  estavam corretos.
- A consulta de umidade de subsolo dava 400 Bad Request por três motivos:
  1. `group_desc: "SOIL"` não existe na taxonomia da API (confirmado via
     `/api/get_param_values/?param=group_desc` — a lista não tem nenhum
     valor contendo "SOIL"). Removido.
  2. O `short_desc` usado, "SOIL, MOISTURE, SUBSOIL - PCT ADEQUATE", tinha
     a ordem das palavras errada. O valor real (confirmado via
     `/api/get_param_values/?param=short_desc`) é
     "SOIL, SUBSOIL - MOISTURE, MEASURED IN PCT ADEQUATE" (e "...SURPLUS"
     para a outra categoria).
  3. O erro real e mais importante: `sector_desc: "ENVIRONMENTAL"` está
     errado — a umidade de solo do Crop Progress fica no mesmo setor das
     condições de lavoura, `sector_desc: "CROPS"` (confirmado testando
     várias combinações de parâmetros contra a API real; com
     `sector_desc="CROPS"` + `agg_level_desc="NATIONAL"` a API retornou
     19 linhas para 2026, uma por semana — consistente com o número de
     relatórios semanais já publicados na safra).

IMPORTANTE PARA QUEM FOR VALIDAR (Claude Code):
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


# O `week_ending` da API do NASS é sempre um domingo (fim da semana de
# levantamento, segunda-domingo). O dashboard rotula cada semana pela
# sexta-feira seguinte (domingo + 5 dias) — confirmado comparando os
# rótulos já existentes no HTML contra as datas reais retornadas pela
# API. Sem esse ajuste, merge_into_series nunca encontra a semana
# correspondente e a atualização vira um no-op silencioso.
DASHBOARD_LABEL_OFFSET_DAYS = 5


def _week_label(week_ending: str) -> str:
    date = datetime.datetime.strptime(week_ending, "%Y-%m-%d")
    date += datetime.timedelta(days=DASHBOARD_LABEL_OFFSET_DAYS)
    return date.strftime("%d/%m")


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
        label = _week_label(r["week_ending"])
        val = float(r["Value"].replace(",", ""))
        by_week.setdefault(label, 0.0)
        by_week[label] += val
    return {k: round(v, 0) for k, v in by_week.items()}


def fetch_subsoil_adequate_surplus():
    rows = _nass_get({
        "source_desc": "SURVEY",
        "sector_desc": "CROPS",
        "short_desc": "SOIL, SUBSOIL - MOISTURE, MEASURED IN PCT ADEQUATE",
        "agg_level_desc": "NATIONAL",
        "freq_desc": "WEEKLY",
        "year": YEAR,
    })
    rows_surplus = _nass_get({
        "source_desc": "SURVEY",
        "sector_desc": "CROPS",
        "short_desc": "SOIL, SUBSOIL - MOISTURE, MEASURED IN PCT SURPLUS",
        "agg_level_desc": "NATIONAL",
        "freq_desc": "WEEKLY",
        "year": YEAR,
    })
    by_week = {}
    for r in rows + rows_surplus:
        label = _week_label(r["week_ending"])
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
