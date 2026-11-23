"""Chamadas favoritas do usuário e histórico de chamadas por tarefa.

favoritas.txt: uma chamada por linha, em seções por idioma ([pt-BR], [en], ...).
Linhas com # são comentários. Caminho: POPUP_FAVORITAS ou a pasta de configuração do
usuário (~/.config/popup/favoritas.txt; Windows: %APPDATA%\\popup\\favoritas.txt), fora
da pasta da skill, para não ser apagado quando a skill é atualizada.

Histórico: guarda as chamadas já mostradas em cada pasta de trabalho. Uma "tarefa"
termina depois de 2 horas sem pop-up naquela pasta. Caminho: POPUP_ESTADO ou
~/.local/state/popup (Windows: %LOCALAPPDATA%\\popup).

Regras (o pop-up é recusado com exit 7):
  - chamada já usada nesta tarefa;
  - favorita logo depois de outra favorita;
  - favorita de outro idioma ou variante.
"""
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
FIM_DA_TAREFA = 2 * 60 * 60  # segundos sem pop-up


# ---------------------------------------------------------------- idioma → seção

def secao(codigo):
    """'pt', 'pt-BR', 'pt_BR.UTF-8' → 'pt-BR'; 'pt-PT' → 'pt-PT'; 'es-mx' → 'es-MX'; 'ja' → 'ja'."""
    if not codigo:
        return None
    limpo = codigo.strip().split(":")[0].split(".")[0].split("@")[0].replace("_", "-")
    partes = [p for p in limpo.split("-") if p]
    if not partes:
        return None
    base = partes[0].lower()
    if len(partes) > 1:
        return f"{base}-{partes[1].upper()}"
    return "pt-BR" if base == "pt" else base


def secoes_validas(codigo):
    """Seções cujas favoritas valem para este idioma.

    A variante exata e, se houver, a seção só com o idioma base ('es-MX' usa [es-MX] e [es]).
    Português é exceção: pt-PT não usa [pt-BR] e vice-versa.
    """
    s = secao(codigo)
    if not s:
        return []
    validas = [s]
    base = s.split("-")[0]
    if "-" in s and base != "pt":
        validas.append(base)
    return validas


def normal(texto):
    return " ".join(texto.split()).casefold()


# ---------------------------------------------------------------- favoritas.txt

def pasta_config():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "popup")


def caminho_favoritas():
    return os.environ.get("POPUP_FAVORITAS") or os.path.join(pasta_config(), "favoritas.txt")


def _modelo():
    """Conteúdo inicial do arquivo: o exemplo que vem com a skill, ou só um cabeçalho."""
    try:
        with open(os.path.join(AQUI, "favoritas.exemplo.txt"), encoding="utf-8") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        return ["# Chamadas favoritas: uma por linha, na seção do idioma.", ""]


def ler():
    """Devolve {seção: [chamadas]}."""
    dados, atual = {}, None
    try:
        with open(caminho_favoritas(), encoding="utf-8") as f:
            for linha in f:
                t = linha.strip()
                if not t or t.startswith("#"):
                    continue
                if t.startswith("[") and t.endswith("]"):
                    atual = secao(t[1:-1]) or t[1:-1]
                    dados.setdefault(atual, [])
                elif atual:
                    dados[atual].append(t)
    except FileNotFoundError:
        pass
    return dados


def secao_de(chamada):
    """Seção onde a chamada é favorita, ou None."""
    alvo = normal(chamada)
    for s, lista in ler().items():
        if any(normal(c) == alvo for c in lista):
            return s
    return None


def secao_para_gravar(codigo):
    """Variante sem seção própria grava na seção do idioma base, se ela existir.

    'ja-JP' com [ja] no arquivo → [ja]. Português nunca mistura pt-BR e pt-PT.
    """
    s = secao(codigo)
    if s and "-" in s and not s.startswith("pt-"):
        dados = ler()
        base = s.split("-")[0]
        if s not in dados and base in dados:
            return base
    return s


def adicionar(codigo, chamada):
    """Acrescenta no fim da seção (cria a seção se faltar). Devolve False se já existia."""
    s = secao_para_gravar(codigo)
    chamada = " ".join(chamada.split())
    if not s or not chamada:
        raise ValueError("idioma e chamada são obrigatórios")
    dados = ler()
    if any(normal(c) == normal(chamada) for v in secoes_validas(codigo) for c in dados.get(v, [])):
        return False
    caminho = caminho_favoritas()
    try:
        with open(caminho, encoding="utf-8") as f:
            linhas = f.read().splitlines()
    except FileNotFoundError:
        linhas = _modelo()
    inicio = next((i for i, l in enumerate(linhas)
                   if l.strip().startswith("[") and secao(l.strip()[1:-1]) == s), None)
    if inicio is None:
        if linhas and linhas[-1].strip():
            linhas.append("")
        linhas += [f"[{s}]", chamada]
    else:
        fim = next((i for i in range(inicio + 1, len(linhas))
                    if linhas[i].strip().startswith("[")), len(linhas))
        ultimo = inicio
        for i in range(inicio + 1, fim):
            if linhas[i].strip():
                ultimo = i
        linhas.insert(ultimo + 1, chamada)
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    return True


def remover(codigo, chamada):
    """Tira a chamada das seções que valem para o idioma. Devolve False se não estava lá."""
    validas = secoes_validas(codigo)
    caminho = caminho_favoritas()
    try:
        with open(caminho, encoding="utf-8") as f:
            linhas = f.read().splitlines()
    except FileNotFoundError:
        return False
    atual, saida, achou = None, [], False
    for l in linhas:
        t = l.strip()
        if t.startswith("[") and t.endswith("]"):
            atual = secao(t[1:-1])
        elif atual in validas and t and not t.startswith("#") and normal(t) == normal(chamada):
            achou = True
            continue
        saida.append(l)
    if achou:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("\n".join(saida) + "\n")
    return achou


# ---------------------------------------------------------------- histórico

def caminho_estado():
    if os.environ.get("POPUP_ESTADO"):
        pasta = os.environ["POPUP_ESTADO"]
    elif sys.platform == "win32":
        pasta = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "popup")
    else:
        pasta = os.path.join(os.environ.get("XDG_STATE_HOME") or
                             os.path.expanduser("~/.local/state"), "popup")
    return os.path.join(pasta, "historico.json")


def _ler_estado():
    try:
        with open(caminho_estado(), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def historico(pasta=None):
    """Chamadas desta tarefa (vazio se a tarefa expirou)."""
    pasta = pasta or os.getcwd()
    itens = _ler_estado().get(pasta, [])
    if itens and time.time() - itens[-1]["t"] > FIM_DA_TAREFA:
        return []
    return itens


def checar(chamada, codigo, pasta=None):
    """Devolve None se pode mostrar, ou o motivo da recusa."""
    itens = historico(pasta)
    alvo = normal(chamada)
    if any(normal(i["chamada"]) == alvo for i in itens):
        return "esta chamada já foi usada nesta tarefa"
    s = secao_de(chamada)
    if s:
        if s not in secoes_validas(codigo):
            return f"esta chamada é favorita do idioma {s}, não do idioma desta conversa"
        if itens and itens[-1].get("favorita"):
            return "o pop-up anterior já usou uma favorita; agora a chamada precisa ser nova"
    return None


def registrar(chamada, pasta=None):
    pasta = pasta or os.getcwd()
    estado = _ler_estado()
    agora = time.time()
    # limpa tarefas encerradas de todas as pastas
    estado = {p: v for p, v in estado.items() if v and agora - v[-1]["t"] <= FIM_DA_TAREFA}
    estado.setdefault(pasta, []).append(
        {"chamada": chamada, "favorita": secao_de(chamada) is not None, "t": agora})
    caminho = caminho_estado()
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=1)
    os.replace(tmp, caminho)
