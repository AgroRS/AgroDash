"""
Bloco 2 · Brasil (Conab) — atualização manual.

A Conab não tem API pública para o progresso semanal de Plantio e
Colheita (só boletins em PDF — ver README, seção "Nota para quem for
validar"). Este script não busca dado nenhum sozinho: ele recebe os
números já extraídos do boletim (que alguém leu e digitou num arquivo
JSON) e injeta no index.html, pra não precisar editar o HTML na mão
toda semana.

Uso:
    python scripts/update_conab.py atualizacao.json ../index.html

Formato do arquivo de atualização (ver scripts/conab_update.example.json):
{
  "season": "2025/26",
  "updates": [
    {
      "crop_stage": "Soja|Colheita",
      "week": "25/06",
      "national_pct": 99.9,
      "states": {"MT": 100, "MS": 99.5}
    }
  ]
}

- "crop_stage": uma das chaves já existentes em BRA_NATIONAL /
  BRA_STATE_SNAPSHOT — "Soja|Plantio", "Soja|Colheita",
  "Algodão|Plantio", "Algodão|Colheita", "Milho 2ª safra|Plantio",
  "Milho 2ª safra|Colheita".
- "week": rótulo "DD/MM", no mesmo formato já usado no arquivo.
- "national_pct": percentual nacional (número). Vai para a série
  semanal de BRA_NATIONAL, na safra indicada em "season", na posição
  correspondente a "week" dentro de `labels`.

IMPORTANTE: `labels` é um molde fixo, compartilhado por todas as
safras, cobrindo toda a janela possível daquele estágio (ex.:
Algodão|Colheita vai de maio a outubro) — as semanas futuras já
existem na lista, só com valor `null` esperando serem preenchidas.
Por isso o script NÃO adiciona semanas novas a `labels`: se o "week"
informado não existir na lista já existente, ele falha com um erro
claro, em vez de arriscar inserir na posição errada e bagunçar a
ordem cronológica do eixo do gráfico (isso realmente aconteceu
testando o script com uma semana fora do padrão de 7 em 7 dias — ver
git log). Se a safra genuinamente precisar de uma janela maior que a
atual (ex.: colheita atrasou além de outubro), estender `labels` é
uma decisão manual, não algo pra esse script inferir sozinho.
- "states": opcional, dict UF -> percentual. Atualiza só as UFs
  informadas em BRA_STATE_SNAPSHOT[crop_stage]["values"] (as outras
  ficam como estavam) e ajusta o campo "year" para "SAFRA (SEMANA)".

Pode ter quantos objetos quiser em "updates" (um por cultura/estágio
que o boletim daquela semana trouxe).
"""
import sys
import json

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from inject_utils import load_html, save_html, replace_const, extract_const


def apply_update(bra_national: dict, bra_state: dict, update: dict, season: str) -> None:
    key = update["crop_stage"]
    week = update["week"]

    if key not in bra_national:
        raise KeyError(
            f"crop_stage desconhecido: {key!r}. "
            f"Chaves existentes: {list(bra_national.keys())}"
        )

    block = bra_national[key]
    labels = block["labels"]
    series = block["series"]

    if week not in labels:
        raise ValueError(
            f"Semana {week!r} não existe em BRA_NATIONAL[{key!r}]['labels']. "
            f"Semanas disponíveis: {labels}. Se a janela da safra precisa ser "
            f"estendida, isso é uma decisão manual (editar `labels` direto), "
            f"não algo pra este script inferir sozinho."
        )
    idx = labels.index(week)

    if season not in series:
        series[season] = [None] * len(labels)

    if update.get("national_pct") is not None:
        series[season][idx] = update["national_pct"]

    states = update.get("states")
    if states:
        snap = bra_state.setdefault(key, {"year": f"{season} ({week})", "values": {}})
        snap["year"] = f"{season} ({week})"
        snap["values"].update(states)


def update_html(html_path: str, payload: dict) -> str:
    season = payload["season"]
    html = load_html(html_path)
    bra_national = extract_const(html, "BRA_NATIONAL")
    bra_state = extract_const(html, "BRA_STATE_SNAPSHOT")

    for update in payload["updates"]:
        apply_update(bra_national, bra_state, update, season)
        states_note = f" · estados: {list(update['states'].keys())}" if update.get("states") else ""
        print(f"[conab] {update['crop_stage']} · semana {update['week']} · safra {season}: "
              f"{update.get('national_pct')}%{states_note}")

    html = replace_const(html, "BRA_NATIONAL", bra_national)
    html = replace_const(html, "BRA_STATE_SNAPSHOT", bra_state)
    return html


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python update_conab.py atualizacao.json index.html")
        sys.exit(1)

    update_path, html_path = sys.argv[1], sys.argv[2]
    with open(update_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    new_html = update_html(html_path, payload)
    save_html(html_path, new_html)
    print(f"[conab] {html_path} atualizado.")
