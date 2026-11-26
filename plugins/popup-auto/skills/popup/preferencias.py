"""Preferência de apresentação do pop-up: window, dialog ou notification.

Arquivo: POPUP_PREFERENCES ou a pasta de configuração do usuário
(~/.config/popup/preferences.txt; Windows: %APPDATA%\\popup\\preferences.txt).
Formato:

    # popup preferences
    mode = window

Precedência: --mode > POPUP_MODE > arquivo > window.
"""
import os
import sys

import favoritas as fav
from textos import env

MODOS = ("window", "dialog", "notification")
PADRAO = "window"


def aviso(msg):
    print(f"popup: {msg}", file=sys.stderr)


def caminho():
    explicito = env("POPUP_PREFERENCES", "POPUP_PREFERENCIAS")
    if explicito:
        return explicito
    return os.path.join(fav.pasta_config(), "preferences.txt")


def ler():
    """Lê o arquivo sem validar o valor; devolve as chaves encontradas."""
    dados = {}
    try:
        with open(caminho(), encoding="utf-8") as f:
            for linha in f:
                t = linha.strip()
                if not t or t.startswith("#"):
                    continue
                if "=" not in t:
                    aviso(f"invalid line in {caminho()}: {t!r}")
                    continue
                chave, valor = t.split("=", 1)
                dados[chave.strip().lower()] = valor.strip().lower()
    except FileNotFoundError:
        pass
    except OSError as e:
        aviso(f"could not read {caminho()} ({e})")
    return dados


def _modo_arquivo():
    valor = ler().get("mode")
    if valor is None:
        return None
    if valor not in MODOS:
        aviso(f"invalid mode in {caminho()}: {valor!r}; using {PADRAO}")
        return None
    return valor


def _modo_env():
    valor = env("POPUP_MODE", "POPUP_MODO")
    if not valor:
        return None
    valor = valor.strip().lower()
    if valor not in MODOS:
        aviso(f"invalid POPUP_MODE: {valor!r}; ignoring it")
        return None
    return valor


def modo(flag=None):
    """Modo efetivo, com a precedência documentada."""
    if flag:
        flag = str(flag).strip().lower()
        if flag in MODOS:
            return flag
        aviso(f"invalid mode: {flag!r}; using {PADRAO}")
        return PADRAO
    return _modo_env() or _modo_arquivo() or PADRAO


def origem(flag=None):
    """De onde veio o modo efetivo: flag, env, file ou default."""
    if flag and str(flag).strip().lower() in MODOS:
        return "flag"
    if _modo_env():
        return "env"
    if _modo_arquivo():
        return "file"
    return "default"


def gravar(novo):
    """Valida e grava o modo de forma atômica. Devolve o modo gravado."""
    novo = str(novo).strip().lower()
    if novo not in MODOS:
        raise ValueError(f"invalid mode: {novo!r} (use {', '.join(MODOS)})")
    destino = caminho()
    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    tmp = f"{destino}.tmp.{os.getpid()}"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("# popup preferences\n")
            f.write(f"mode = {novo}\n")
        os.replace(tmp, destino)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
    return novo
