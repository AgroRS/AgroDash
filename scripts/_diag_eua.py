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

    print(f"\n=== short_desc brutos retornados para SUBSOLO ADEQUATE (year={feu.YEAR}) ===")
    rows_a = feu._nass_get({
        "source_desc": "SURVEY",
        "sector_desc": "ENVIRONMENTAL",
        "group_desc": "SOIL",
        "short_desc": "SOIL, MOISTURE, SUBSOIL - PCT ADEQUATE",
        "agg_level_desc": "NATIONAL",
        "freq_desc": "WEEKLY",
        "year": feu.YEAR,
    })
    print(f"total de linhas: {len(rows_a)}")
    if rows_a:
        print("exemplo:", json.dumps(rows_a[0], ensure_ascii=False))

    print("\n=== fetch_subsoil_adequate_surplus() ===")
    subsolo = feu.fetch_subsoil_adequate_surplus()
    for wk in sorted(subsolo.keys()):
        print(f"  {wk}: {subsolo[wk]}")

    print("\n=== update_html completo (numa cópia) ===")
    shutil.copyfile(src, COPY)
    new_html = feu.update_html(COPY)
    condition = extract_const(new_html, "EUA_CONDITION")
    subsolo_full = extract_const(new_html, "EUA_SUBSOLO")
    for label in ["Soja", "Milho"]:
        series = condition[label][feu.CURRENT_SEASON_LABEL]
        print(f"  EUA_CONDITION[{label}][{feu.CURRENT_SEASON_LABEL}] últimos 6: {series[-6:]}")
    print(f"  EUA_SUBSOLO[{feu.CURRENT_SEASON_LABEL}] últimos 6: {subsolo_full[feu.CURRENT_SEASON_LABEL][-6:]}")


if __name__ == "__main__":
    main()
