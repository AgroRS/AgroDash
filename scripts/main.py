"""
Orquestrador — roda os fetchers habilitados, em ordem, sobre o mesmo
arquivo HTML. Cada fetcher é independente: se um falhar, os outros ainda
devem rodar (fica registrado no log do GitHub Actions, mas não trava tudo).

Uso:
    python scripts/main.py dashagro_completo.html
"""
import sys
import traceback

import fetch_clima
import fetch_hedge_funds
import fetch_oferta_demanda
import fetch_prices
import fetch_eua_condicoes


def run_step(name, fn, path):
    print(f"\n=== {name} ===")
    try:
        fn(path)
        print(f"[{name}] OK")
        return True
    except Exception as e:
        print(f"[{name}] FALHOU: {e}")
        traceback.print_exc()
        return False


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "dashagro_completo.html"

    results = {}
    results["clima"] = run_step(
        "clima (NOAA)",
        lambda p: fetch_clima.save_html(p, fetch_clima.update_html(p)),
        path,
    )
    results["hedge_funds"] = run_step(
        "hedge_funds (CFTC)",
        lambda p: fetch_hedge_funds.save_html(p, fetch_hedge_funds.update_html(p)),
        path,
    )
    results["oferta_demanda"] = run_step(
        "oferta_demanda (USDA/PSD)",
        lambda p: fetch_oferta_demanda.save_html(p, fetch_oferta_demanda.update_html(p)),
        path,
    )
    results["precos"] = run_step(
        "precos (CBOT/ICE/USD-BRL)",
        lambda p: fetch_prices.save_html(p, fetch_prices.update_html(p)),
        path,
    )
    results["eua_condicoes"] = run_step(
        "eua_condicoes (NASS)",
        lambda p: fetch_eua_condicoes.save_html(p, fetch_eua_condicoes.update_html(p)),
        path,
    )

    print("\n=== Resumo ===")
    for k, v in results.items():
        print(f"  {k}: {'OK' if v else 'FALHOU'}")

    # sai com erro se TODOS falharam (evita commit vazio/sem sentido);
    # se só alguns falharam, ainda vale commitar o que funcionou
    if not any(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
