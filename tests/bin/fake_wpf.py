#!/usr/bin/env python3
"""powershell falso para os testes do Windows nativo (WPF e WinForms).

Entende as duas formas de chamada:
  -File <script>       interface WPF (lê o .ps1, confere o BOM e extrai dados/XAML)
  -EncodedCommand ...  interface WinForms (script em base64/UTF-16)

Registra o script e os dados em FAKE_LOG e responde como a fila mandar
(FAKE_RESP: linhas "código|saída").
"""
import base64
import json
import os
import re
import sys

a = sys.argv[1:]
flags = [x for x in a if x.startswith("-")]
registro = {"prog": "powershell", "flags": flags, "cwd": os.getcwd()}

if "-EncodedCommand" in a:
    script = base64.b64decode(a[a.index("-EncodedCommand") + 1]).decode("utf-16-le")
    registro.update(forma="encoded", caminho=None, bom=None)
    m = re.search(r"FromBase64String\('([^']*)'\)", script)
    dados = json.loads(base64.b64decode(m.group(1)).decode("utf-8")) if m else None
    xaml = None
else:
    caminho = a[a.index("-File") + 1]
    bruto = open(caminho, "rb").read()
    script = bruto.decode("utf-8-sig")
    registro.update(forma="file", caminho=caminho, bom=bruto.startswith(b"\xef\xbb\xbf"))
    dados = xaml = None
    for b64 in re.findall(r"FromBase64String\('([^']*)'\)", script):
        try:
            texto = base64.b64decode(b64).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        if texto.lstrip().startswith("{"):
            dados = json.loads(texto)
        elif texto.lstrip().startswith("<"):
            xaml = texto

registro.update(
    dados=dados,
    xaml=xaml,
    script=script,
    script_ok=("ShowDialog" in script and "__DADOS_B64__" not in script
               and "__XAML_B64__" not in script),
    trap=script.lstrip().splitlines()[1].startswith("trap"),
)
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps(registro, ensure_ascii=False) + "\n")

fila = os.environ["FAKE_RESP"]
linhas = open(fila).read().splitlines()
rc, _, out = (linhas.pop(0) if linhas else "5|").partition("|")
open(fila, "w").write("\n".join(linhas))
if out:
    sys.stdout.write(out)
sys.exit(int(rc))
