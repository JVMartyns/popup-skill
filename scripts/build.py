#!/usr/bin/env python3
"""Gera os dois plugins do Claude Code a partir de skills/popup/ (a fonte única).

  plugins/popup/       só roda com /popup (disable-model-invocation: true)
  plugins/popup-auto/  o Claude pode ativar sozinho (mesmo SKILL.md da fonte)

Uso:
  scripts/build.py           gera/atualiza plugins/
  scripts/build.py --check   não grava; sai com 1 se plugins/ estiver desatualizado (CI)
"""
import filecmp
import json
import os
import shutil
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTE = os.path.join(RAIZ, "skills", "popup")
IGNORAR = shutil.ignore_patterns("__pycache__", "*.pyc")

DESC_MANUAL = ("Ask the user the task's questions through desktop pop-up windows "
               "(Linux GTK/KDE, macOS, Windows) instead of the terminal. "
               "Runs only when the user invokes it with /popup.")

PLUGINS = {
    "popup": {
        "description": "Ask questions through desktop pop-ups instead of the terminal "
                       "(agents running on your own computer, such as Claude Code). "
                       "Manual: runs only when you type /popup.",
        "manual": True,
    },
    "popup-auto": {
        "description": "Ask questions through desktop pop-ups instead of the terminal "
                       "(agents running on your own computer, such as Claude Code). "
                       "Claude can turn it on by itself when you say you'll be away "
                       "or ask for pop-ups.",
        "manual": False,
    },
}


def versao():
    with open(os.path.join(RAIZ, "VERSION")) as f:
        return f.read().strip()


def frontmatter_manual(texto):
    """Troca a description e acrescenta disable-model-invocation: true."""
    assert texto.startswith("---\n")
    fim = texto.index("\n---\n", 4)
    linhas = texto[4:fim].splitlines()
    saida = []
    for l in linhas:
        if l.startswith("description:"):
            saida.append(f"description: {DESC_MANUAL}")
            saida.append("disable-model-invocation: true")
        elif not l.startswith("disable-model-invocation:"):
            saida.append(l)
    return "---\n" + "\n".join(saida) + texto[fim:]


def gerar(destino):
    for nome, cfg in PLUGINS.items():
        base = os.path.join(destino, nome)
        skill = os.path.join(base, "skills", "popup")
        shutil.copytree(FONTE, skill, ignore=IGNORAR)
        if cfg["manual"]:
            caminho = os.path.join(skill, "SKILL.md")
            with open(caminho, encoding="utf-8") as f:
                texto = f.read()
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(frontmatter_manual(texto))
        os.makedirs(os.path.join(base, ".claude-plugin"))
        manifesto = {
            "name": nome,
            "version": versao(),
            "description": cfg["description"],
            "author": {"name": "JVMartyns"},
            "license": "MIT",
            "keywords": ["popup", "questions", "gtk", "notifications", "i18n"],
        }
        with open(os.path.join(base, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as f:
            json.dump(manifesto, f, ensure_ascii=False, indent=2)
            f.write("\n")


def iguais(a, b):
    cmp = filecmp.dircmp(a, b, ignore=["__pycache__"])
    if cmp.left_only or cmp.right_only:
        return False
    _, diferentes, erros = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    if diferentes or erros:
        return False
    return all(iguais(os.path.join(a, d), os.path.join(b, d)) for d in cmp.common_dirs)


def main():
    alvo = os.path.join(RAIZ, "plugins")
    with tempfile.TemporaryDirectory() as tmp:
        novo = os.path.join(tmp, "plugins")
        gerar(novo)
        if "--check" in sys.argv:
            if os.path.isdir(alvo) and iguais(novo, alvo):
                print("plugins/ está em dia com skills/popup/")
                return
            print("plugins/ está desatualizado: rode scripts/build.py e faça commit", file=sys.stderr)
            sys.exit(1)
        if os.path.isdir(alvo):
            shutil.rmtree(alvo)
        shutil.copytree(novo, alvo)
        # mantém o bit de execução dos scripts
        for nome in PLUGINS:
            for arq in ("popup.py", "ui_gtk.py"):
                os.chmod(os.path.join(alvo, nome, "skills", "popup", arq), 0o755)
    print(f"plugins/ gerado (versão {versao()})")


if __name__ == "__main__":
    main()
