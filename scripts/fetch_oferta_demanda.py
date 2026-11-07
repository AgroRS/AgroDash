"""
Bloco 3 · Oferta & Demanda — atualiza CROPS (soja/milho/algodão) a partir
da API oficial do USDA/FAS PSD (Production, Supply and Distribution).

Validado com chamada real (via GitHub Actions) em 2026-08-10:
- Host/autenticação corretos: https://api.fas.usda.gov/api, header
  "X-Api-Key" (não "API_KEY" e não apps.fas.usda.gov/PSDOnlineDataServices
  — essa API legada foi descontinuada e responde 403 "Bad API Key" mesmo
  com uma chave válida).
- Endpoint por commodity/ano: /api/psd/commodity/{code}/world/year/{year}
  — devolve todos os atributos de uma vez (não um por chamada).
- Nomes de atributo não vêm na resposta (só attributeId numérico); o
  mapeamento id -> nome vem de /api/psd/commodityAttributes.
- Códigos de commodity confirmados contra dados reais: soja=2222000,
  milho=0440000 (o zero à esquerda é obrigatório — sem ele a API responde
  404), algodao=2631000.

Ainda não automatizado (fica para uma segunda iteração): prodCountry,
endCountry, top5Importers, topCrush, price, e as duas colunas "correntes"
(que na versão atual do site vêm de circulares mensais específicas, não
da consulta anual padrão do PSD) — essas colunas continuam repetindo o
valor mais recente disponível até serem automatizadas.

Estrutura esperada de CROPS (ver index.html, bloco b3):
    CROPS = {
      "soja": {
        "years": [...], "cur": "...", "cur2": "...",
        "world": {ano: {"beg","prod","cons","end"}},
        "prodCountry": {ano: {"Brasil","EUA","Argentina","China","Outros"}},
        "endCountry": {ano: {"Brasil","EUA","Argentina","China"}},
        "top5Importers": {...}, "topCrush": {...}, "price": {...}, ...
      },
      "milho": {...}, "algodao": {...}
    }
"""
import os
import sys
import time
import requests

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from inject_utils import load_html, save_html, replace_const, extract_const

PSD_API_KEY = os.environ.get("USDA_PSD_API_KEY")
PSD_BASE = "https://api.fas.usda.gov/api"

COMMODITY_CODES = {
    "soja": "2222000",     # Oilseed, Soybean
    "milho": "0440000",    # Corn
    "algodao": "2631000",  # Cotton
}

ATTR_NAMES = {
    "beg": "Beginning Stocks",
    "prod": "Production",
    "cons": "Domestic Consumption",
    "end": "Ending Stocks",
}

# a API do USDA/PSD reporta essas quantidades em milhares de unidade (1000 MT
# pra soja/milho, 1000 fardos de 480 lb pro algodão) — o dashboard exibe em
# milhões, daí a divisão. Confirmado comparando contra a safra corrente (que
# já tinha sido preenchida manualmente na escala certa): sem essa divisão,
# as safras fechadas (auto-fetch) ficavam 1000x maiores que a safra corrente
# (manual) na mesma tabela.
UNIT_DIVISOR = 1000

HEADERS = {"X-Api-Key": PSD_API_KEY, "Accept": "application/json"} if PSD_API_KEY else {}


def _get_with_retry(url: str, tries: int = 5, timeout: int = 60):
    """A api.fas.usda.gov tem se mostrado instável (timeouts e respostas
    vazias intermitentes) — retry com backoff evita que uma falha passageira
    derrube a atualização inteira."""
    last_err = None
    for attempt in range(tries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            if resp.status_code == 200 and resp.text.strip():
                return resp
            last_err = RuntimeError(f"status={resp.status_code} body={resp.text[:200]!r}")
        except requests.exceptions.RequestException as e:
            last_err = e
        if attempt < tries - 1:
            time.sleep(5 * (attempt + 1))
    raise last_err


def fetch_attribute_map() -> dict:
    """attributeId -> attributeName, válido para todos os commodities."""
    resp = _get_with_retry(f"{PSD_BASE}/psd/commodityAttributes")
    return {row["attributeId"]: row["attributeName"] for row in resp.json()}


def fetch_commodity_year(commodity_code: str, market_year: int):
    url = f"{PSD_BASE}/psd/commodity/{commodity_code}/world/year/{market_year}"
    resp = _get_with_retry(url)
    return resp.json()


def build_crop_update(commodity_code: str, years: list, attr_map: dict):
    world = {}
    for year in years:
        rows = fetch_commodity_year(commodity_code, year)
        attrs = {}
        for row in rows:
            name = attr_map.get(row["attributeId"])
            if name in ATTR_NAMES.values():
                attrs[name] = row["value"]
        world[year] = {
            key: (round(attrs[name] / UNIT_DIVISOR, 3) if attrs.get(name) is not None else None)
            for key, name in ATTR_NAMES.items()
        }
    return world


def update_html(html_path: str) -> str:
    if not PSD_API_KEY:
        raise RuntimeError(
            "USDA_PSD_API_KEY não encontrada nas variáveis de ambiente. "
            "Cadastre uma chave grátis em https://apps.fas.usda.gov/opendataweb/home "
            "e configure como Secret no GitHub (ver README)."
        )

    html = load_html(html_path)
    crops = extract_const(html, "CROPS")
    attr_map = fetch_attribute_map()

    for key, code in COMMODITY_CODES.items():
        years = crops[key]["years"]  # reaproveita a lista de safras já presente
        year_ints = [int(y.split("/")[0]) for y in years]
        world_update = build_crop_update(code, year_ints, attr_map)
        # atualiza só os campos "world" por enquanto (produção/consumo/estoque
        # mundial); prodCountry/endCountry/top5Importers/topCrush ficam para
        # uma segunda iteração deste script.
        for year_label, year_int in zip(years, year_ints):
            if year_int in world_update:
                crops[key]["world"][year_label] = world_update[year_int]

    html = replace_const(html, "CROPS", crops)
    return html


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../members/mig7lpqvfqpa36k5v3u8rc98/index.html"
    new_html = update_html(path)
    save_html(path, new_html)
    print(f"[oferta_demanda] CROPS (world) atualizado em {path}")
