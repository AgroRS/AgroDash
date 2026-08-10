"""
Script de DIAGNÓSTICO temporário — não faz parte da automação normal.
Testa, contra a internet real (via GitHub Actions), duas gerações possíveis
da API do USDA/FAS PSD que apareceram em fontes diferentes, para descobrir
qual está de fato ativa e qual o formato real de resposta:

  A) apps.fas.usda.gov/OpenData/api/psd/...   header: API_KEY
  B) api.fas.usda.gov/api/psd/...             header: X-Api-Key

Remover este arquivo (e o workflow scripts-diag.yml) depois de usar.
"""
import os
import requests

API_KEY = os.environ.get("USDA_PSD_API_KEY")

CANDIDATES = [
    {
        "label": "A) apps.fas.usda.gov/OpenData (API_KEY)",
        "base": "https://apps.fas.usda.gov/OpenData/api",
        "header_name": "API_KEY",
    },
    {
        "label": "B) api.fas.usda.gov (X-Api-Key)",
        "base": "https://api.fas.usda.gov/api",
        "header_name": "X-Api-Key",
    },
    {
        "label": "C) legado apps.fas.usda.gov/PSDOnlineDataServices (API_KEY)",
        "base": "https://apps.fas.usda.gov/PSDOnlineDataServices/api",
        "header_name": "API_KEY",
        "legacy_path": True,
    },
]

SOYBEAN_CODE = "2222000"
YEAR = 2023


def probe(candidate):
    print(f"\n=== {candidate['label']} ===")
    headers = {candidate["header_name"]: API_KEY, "Accept": "application/json"}

    if candidate.get("legacy_path"):
        url = f"{candidate['base']}/CommodityData/GetCommodityDataByYear"
        params = {"commodityCode": SOYBEAN_CODE, "marketYear": YEAR}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=20)
            print(f"GET {r.url}")
            print(f"status={r.status_code}")
            print(f"body[:500]={r.text[:500]!r}")
        except Exception as e:
            print(f"ERRO: {e!r}")
        return

    # commodityAttributes (mapa attributeId -> nome)
    try:
        url_attrs = f"{candidate['base']}/psd/commodityAttributes"
        r = requests.get(url_attrs, headers=headers, timeout=20)
        print(f"GET {url_attrs}")
        print(f"status={r.status_code}")
        print(f"body[:500]={r.text[:500]!r}")
    except Exception as e:
        print(f"ERRO commodityAttributes: {e!r}")

    # dados mundiais de soja para 2023
    try:
        url_world = f"{candidate['base']}/psd/commodity/{SOYBEAN_CODE}/world/year/{YEAR}"
        r = requests.get(url_world, headers=headers, timeout=20)
        print(f"GET {url_world}")
        print(f"status={r.status_code}")
        print(f"body[:800]={r.text[:800]!r}")
    except Exception as e:
        print(f"ERRO world/year: {e!r}")


def main():
    if not API_KEY:
        print("USDA_PSD_API_KEY não configurada — abortando diagnóstico.")
        return
    for c in CANDIDATES:
        probe(c)


if __name__ == "__main__":
    main()
