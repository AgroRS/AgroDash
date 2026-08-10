"""
Bloco 3 · Oferta & Demanda — atualiza CROPS (soja/milho/algodão) a partir
da API oficial do USDA/FAS PSD Online.

*** ESTE SCRIPT TEM CONFIANÇA MENOR QUE OS OUTROS DOIS (clima/hedge_funds)
    E PRECISA DE VALIDAÇÃO CUIDADOSA PELO CLAUDE CODE ANTES DE ENTRAR NO
    AGENDAMENTO AUTOMÁTICO. ***

Por quê:
1. A API do PSD Online exige uma API key gratuita, obtida em:
   https://apps.fas.usda.gov/psdonline/app/index.html -> "API" no menu.
   Cadastro simples, mas precisa ser feito manualmente uma vez.
2. O endpoint e o formato exato de resposta não puderam ser testados a
   partir do ambiente do Claude.ai nesta conversa — o que está abaixo é
   construído a partir da documentação pública da API, não de uma chamada
   real bem-sucedida. Validar contra a doc oficial:
   https://apps.fas.usda.gov/psdonline/app/index.html#/app/about
3. O Bloco 3 tem duas colunas "correntes" (ex: Jun/26 e Jul/26) que vêm,
   na versão atual do site, de circulares mensais específicas (Oilseeds/
   Grain/Cotton), não da consulta anual padrão do PSD. Uma automação
   completa a essas duas colunas mensais é mais complexa; a versão inicial
   deste script atualiza as SAFRAS FECHADAS (anos completos) via PSD, e
   repete o valor mais recente disponível nas colunas "corrente" até essa
   parte ser refinada.

Estrutura esperada de CROPS (ver dashagro_completo.html, bloco b3):
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
import requests

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from inject_utils import load_html, save_html, replace_const, extract_const

PSD_API_KEY = os.environ.get("USDA_PSD_API_KEY")
PSD_BASE = "https://apps.fas.usda.gov/PSDOnlineDataServices/api"

# Códigos de commodity do PSD (conferir contra a doc oficial — estes são os
# valores usualmente documentados, mas precisam de confirmação):
COMMODITY_CODES = {
    "soja": "2222000",     # Oilseed, Soybean
    "milho": "0440000",    # Corn
    "algodao": "2631000",  # Cotton
}

HEADERS = {"API_KEY": PSD_API_KEY} if PSD_API_KEY else {}


def fetch_commodity_year(commodity_code: str, market_year: int):
    """Busca os dados de um commodity para um marketing year específico.
    ENDPOINT A CONFIRMAR — ver docstring do módulo."""
    url = f"{PSD_BASE}/CommodityData/GetCommodityDataByYear"
    params = {"commodityCode": commodity_code, "marketYear": market_year}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_crop_update(commodity_code: str, years: list):
    """Monta o dicionário world/prodCountry/endCountry a partir das
    respostas da API, para os anos pedidos. Implementação de referência —
    a mixagem exata de campos da resposta da API PSD para os attributes
    (Beginning Stocks, Production, Domestic Consumption, Ending Stocks)
    precisa ser conferida e ajustada por quem for validar isso."""
    world = {}
    for year in years:
        data = fetch_commodity_year(commodity_code, year)
        # TODO: mapear os campos reais da resposta da API para:
        #   beg  = Beginning Stocks
        #   prod = Production
        #   cons = Domestic Consumption
        #   end  = Ending Stocks
        # Estrutura de exemplo (ajustar conforme resposta real):
        attrs = {row["attributeName"]: row["value"] for row in data}
        world[year] = {
            "beg": attrs.get("Beginning Stocks"),
            "prod": attrs.get("Production"),
            "cons": attrs.get("Domestic Consumption"),
            "end": attrs.get("Ending Stocks"),
        }
    return world


def update_html(html_path: str) -> str:
    if not PSD_API_KEY:
        raise RuntimeError(
            "USDA_PSD_API_KEY não encontrada nas variáveis de ambiente. "
            "Cadastre uma chave grátis em https://apps.fas.usda.gov/psdonline/ "
            "e configure como Secret no GitHub (ver README)."
        )

    html = load_html(html_path)
    crops = extract_const(html, "CROPS")

    for key, code in COMMODITY_CODES.items():
        years = crops[key]["years"]  # reaproveita a lista de safras já presente
        year_ints = [int(y.split("/")[0]) for y in years]
        world_update = build_crop_update(code, year_ints)
        # atualiza só os campos "world" por enquanto (produção/consumo/estoque
        # mundial); prodCountry/endCountry/top5Importers/topCrush ficam para
        # uma segunda iteração deste script, depois que o endpoint acima
        # estiver validado.
        for year_label, year_int in zip(years, year_ints):
            if year_int in world_update:
                crops[key]["world"][year_label] = world_update[year_int]

    html = replace_const(html, "CROPS", crops)
    return html


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "dashagro_completo.html"
    new_html = update_html(path)
    save_html(path, new_html)
    print(f"[oferta_demanda] CROPS (world) atualizado em {path}")
