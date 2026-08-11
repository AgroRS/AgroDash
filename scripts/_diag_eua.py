"""
Script de DIAGNÓSTICO temporário — não faz parte da automação normal.
Roda fetch_eua_condicoes.py contra uma cópia do index.html (não
sobrescreve o arquivo real) e imprime valores brutos da API do NASS e o
resultado processado, pra validar contra fonte pública antes de confiar
no script.

Remover este arquivo (e o workflow scripts-diag.yml) depois de usar.
"""
import json
import shutil
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import fetch_eua_condicoes as feu
from inject_utils import load_html, extract_const

COPY = "_diag_index_copy.html"


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "index.html"

    print(f"NASS_API_KEY presente? {'sim' if feu.NASS_API_KEY else 'NAO'}")
    if not feu.NASS_API_KEY:
        print("Abortando diagnóstico — sem chave não dá pra chamar a API.")
        return

    print(f"\n=== short_desc brutos retornados para SOYBEANS (year={feu.YEAR}) ===")
    rows = feu._nass_get({
        "source_desc": "SURVEY",
        "sector_desc": "CROPS",
        "commodity_desc": "SOYBEANS",
        "statisticcat_desc": "CONDITION",
        "agg_level_desc": "NATIONAL",
        "freq_desc": "WEEKLY",
        "year": feu.YEAR,
    })
    print(f"total de linhas: {len(rows)}")
    descs = sorted(set(r["short_desc"] for r in rows))
    for d in descs:
        print(f"  {d!r}")
    if rows:
        print("exemplo de linha completa:", json.dumps(rows[0], ensure_ascii=False))

    print("\n=== fetch_condition_good_excellent(SOYBEANS) ===")
    soja = feu.fetch_condition_good_excellent("SOYBEANS")
    for wk in sorted(soja.keys()):
        print(f"  {wk}: {soja[wk]}")

    print("\n=== fetch_condition_good_excellent(CORN) ===")
    milho = feu.fetch_condition_good_excellent("CORN")
    for wk in sorted(milho.keys()):
        print(f"  {wk}: {milho[wk]}")

    print(f"\n=== investigação: parâmetros válidos para umidade de solo ===")
    try:
        r = feu.requests.get(
            "https://quickstats.nass.usda.gov/api/get_param_values/",
            params={"key": feu.NASS_API_KEY, "param": "group_desc"},
            timeout=30,
        )
        print(f"get_param_values(group_desc) status={r.status_code}")
        groups = r.json().get("group_desc", [])
        soil_groups = [g for g in groups if "SOIL" in g.upper()]
        print(f"grupos contendo SOIL: {soil_groups}")
    except Exception as e:
        print(f"ERRO get_param_values(group_desc): {e!r}")

    try:
        r = feu.requests.get(
            "https://quickstats.nass.usda.gov/api/get_param_values/",
            params={"key": feu.NASS_API_KEY, "param": "short_desc"},
            timeout=60,
        )
        print(f"get_param_values(short_desc) status={r.status_code}")
        all_short = r.json().get("short_desc", [])
        subsoil_matches = [s for s in all_short if "SUBSOIL" in s.upper()]
        print(f"short_desc contendo SUBSOIL ({len(subsoil_matches)}):")
        for s in subsoil_matches:
            print(f"  {s!r}")
    except Exception as e:
        print(f"ERRO get_param_values(short_desc): {e!r}")

    print(f"\n=== tentativa direta (year={feu.YEAR}, sem group_desc) ===")
    try:
        rows_probe = feu._nass_get({
            "source_desc": "SURVEY",
            "sector_desc": "ENVIRONMENTAL",
            "short_desc": "SOIL, MOISTURE, SUBSOIL - PCT ADEQUATE",
            "freq_desc": "WEEKLY",
            "year": feu.YEAR,
        })
        print(f"OK, total de linhas: {len(rows_probe)}")
        if rows_probe:
            print("exemplo:", json.dumps(rows_probe[0], ensure_ascii=False))
    except Exception as e:
        print(f"ERRO: {e!r}")

    print("\n=== fetch_subsoil_adequate_surplus() ===")
    try:
        subsolo = feu.fetch_subsoil_adequate_surplus()
        for wk in sorted(subsolo.keys()):
            print(f"  {wk}: {subsolo[wk]}")
    except Exception as e:
        print(f"ERRO: {e!r}")

    print("\n=== update_html completo (numa cópia) ===")
    try:
        shutil.copyfile(src, COPY)
        new_html = feu.update_html(COPY)
        condition = extract_const(new_html, "EUA_CONDITION")
        subsolo_full = extract_const(new_html, "EUA_SUBSOLO")
        for label in ["Soja", "Milho"]:
            series = condition[label][feu.CURRENT_SEASON_LABEL]
            print(f"  EUA_CONDITION[{label}][{feu.CURRENT_SEASON_LABEL}] últimos 6: {series[-6:]}")
        print(f"  EUA_SUBSOLO[{feu.CURRENT_SEASON_LABEL}] últimos 6: {subsolo_full[feu.CURRENT_SEASON_LABEL][-6:]}")
    except Exception as e:
        print(f"ERRO: {e!r}")


if __name__ == "__main__":
    main()
