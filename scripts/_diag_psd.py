"""
Script de DIAGNÓSTICO temporário — não faz parte da automação normal.
Confirmado: api.fas.usda.gov + header X-Api-Key é a API ativa.
Agora extrai os attributeIds exatos que fetch_oferta_demanda.py precisa
(Beginning Stocks, Production, Domestic Consumption, Ending Stocks) e
mostra o payload mundial completo pra soja/milho/algodão em 2023.

Remover este arquivo (e o workflow scripts-diag.yml) depois de usar.
"""
import json
import os
import requests

API_KEY = os.environ.get("USDA_PSD_API_KEY")
BASE = "https://api.fas.usda.gov/api"
HEADERS = {"X-Api-Key": API_KEY, "Accept": "application/json"}

WANTED_ATTRS = [
    "Beginning Stocks",
    "Production",
    "Domestic Consumption",
    "Ending Stocks",
    "Total Distribution",
    "Imports",
    "Exports",
]

COMMODITY_CODES = {
    "soja": "2222000",
    "milho": "0440000",
    "algodao": "2631000",
}


def main():
    if not API_KEY:
        print("USDA_PSD_API_KEY não configurada.")
        return

    r = requests.get(f"{BASE}/psd/commodityAttributes", headers=HEADERS, timeout=20)
    attrs = r.json()
    print(f"Total de atributos: {len(attrs)}")
    name_to_id = {}
    for a in attrs:
        if a["attributeName"] in WANTED_ATTRS:
            print(f"  {a['attributeId']:>4} -> {a['attributeName']}")
            name_to_id[a["attributeName"]] = a["attributeId"]

    for label, code in COMMODITY_CODES.items():
        print(f"\n=== {label} (code={code}) world/year/2023 ===")
        r = requests.get(f"{BASE}/psd/commodity/{code}/world/year/2023", headers=HEADERS, timeout=20)
        print(f"status={r.status_code}")
        if r.status_code != 200:
            print(f"body={r.text[:300]!r}")
            continue
        data = r.json()
        print(f"registros retornados: {len(data)}")
        by_attr = {}
        for row in data:
            by_attr.setdefault(row["attributeId"], []).append(row)
        for name, attr_id in name_to_id.items():
            rows = by_attr.get(attr_id, [])
            print(f"  {name} (id={attr_id}): {[ (row['unitId'], row['value']) for row in rows ]}")

    # também testa se o commodityCode do milho com zero à esquerda funciona
    print("\n=== teste commodityCode milho SEM zero à esquerda (440000) ===")
    r = requests.get(f"{BASE}/psd/commodity/440000/world/year/2023", headers=HEADERS, timeout=20)
    print(f"status={r.status_code}, registros={len(r.json()) if r.status_code == 200 else r.text[:200]}")


if __name__ == "__main__":
    main()
