#!/usr/bin/env python3
"""powershell.exe falso: decodifica -EncodedCommand, registra o script e os dados, e
responde como a fila mandar (FAKE_RESP: linhas "código|saída")."""
import base64, json, os, re, sys
a = sys.argv[1:]
script = base64.b64decode(a[a.index("-EncodedCommand") + 1]).decode("utf-16-le")
m = re.search(r"FromBase64String\('([^']*)'\)", script)
dados = json.loads(base64.b64decode(m.group(1)).decode("utf-8")) if m else None
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps({"prog": "powershell.exe", "flags": [x for x in a if x.startswith("-")],
                        "dados": dados, "script_ok": "ShowDialog" in script and "__DADOS_B64__" not in script,
                        "trap": script.lstrip().splitlines()[1].startswith("trap"),
                        "cwd": os.getcwd()}, ensure_ascii=False) + "\n")
fila = os.environ["FAKE_RESP"]
linhas = open(fila).read().splitlines()
rc, _, out = (linhas.pop(0) if linhas else "5|").partition("|")
open(fila, "w").write("\n".join(linhas))
if out:
    sys.stdout.write(out)  # o script real usa [Console]::Out.Write, sem quebra de linha
sys.exit(int(rc))
