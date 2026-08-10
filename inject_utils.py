"""
Utilitário compartilhado: encontra `const NOME = {...};` ou `const NOME = [...];`
dentro do dashagro_completo.html e substitui pelo novo valor (em JSON),
preservando todo o resto do arquivo intacto.

Isso é usado por todos os scripts fetch_*.py para gravar o dado atualizado
de volta no HTML sem precisar reescrever o arquivo inteiro na mão.
"""
import json
import re


def _find_marker_pos(html: str, marker: str, occurrence: int) -> int:
    """Acha a posição de início da N-ésima ocorrência do marcador (1-indexed).
    Necessário porque blocos diferentes do dashagro_completo.html podem usar
    o mesmo nome de variável dentro de escopos (IIFE) separados — ex: tanto
    o Bloco 4 quanto o Bloco 5 têm um `const DATA = {...}` próprio."""
    pos = -1
    for _ in range(occurrence):
        pos = html.index(marker, pos + 1)
    return pos


def replace_const(html: str, varname: str, new_value, occurrence: int = 1) -> str:
    """
    Substitui `const {varname} = <json>;` por `const {varname} = <novo_json>;`
    Faz o parsing por contagem de chaves/colchetes (não por regex simples),
    porque o conteúdo pode ter aspas e caracteres especiais que confundem
    uma regex ingênua.

    `occurrence`: qual ocorrência da variável substituir, contando a partir
    de 1 — necessário quando o mesmo nome (ex: DATA) aparece em mais de um
    bloco/IIFE do arquivo. Ver README para a tabela de qual bloco usa qual
    ocorrência.
    """
    marker = f"const {varname} = "
    start = _find_marker_pos(html, marker, occurrence)
    value_start = start + len(marker)

    # descobre se é objeto {} ou lista []
    first_char = html[value_start]
    open_char, close_char = ("{", "}") if first_char == "{" else ("[", "]")

    depth = 0
    i = value_start
    in_string = False
    escaped = False
    while i < len(html):
        c = html[i]
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == open_char:
                depth += 1
            elif c == close_char:
                depth -= 1
                if depth == 0:
                    i += 1
                    break
        i += 1

    value_end = i  # posição logo após o fechamento

    new_json = json.dumps(new_value, ensure_ascii=False)
    return html[:value_start] + new_json + html[value_end:]


def load_html(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_html(path: str, html: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def extract_const(html: str, varname: str, occurrence: int = 1):
    """Lê o valor atual de `const NOME = ...;` sem alterar nada — útil para
    comparar/validar antes de sobrescrever. Ver `replace_const` sobre o
    parâmetro `occurrence`."""
    marker = f"const {varname} = "
    start = _find_marker_pos(html, marker, occurrence)
    value_start = start + len(marker)
    first_char = html[value_start]
    open_char, close_char = ("{", "}") if first_char == "{" else ("[", "]")
    depth = 0
    i = value_start
    in_string = False
    escaped = False
    while i < len(html):
        c = html[i]
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == open_char:
                depth += 1
            elif c == close_char:
                depth -= 1
                if depth == 0:
                    i += 1
                    break
        i += 1
    return json.loads(html[value_start:i])
