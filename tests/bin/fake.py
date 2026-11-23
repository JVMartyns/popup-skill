#!/usr/bin/env python3
import json, os, sys
nome = os.path.basename(sys.argv[0])
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps({"prog": nome, "argv": sys.argv[1:]}, ensure_ascii=False) + "\n")
fila = os.environ["FAKE_RESP"]
linhas = open(fila).read().splitlines()
rc, _, out = (linhas.pop(0) if linhas else "5|").partition("|")
open(fila, "w").write("\n".join(linhas))
if out == "<FALHA_TELA>":
    print("Gtk-WARNING: Failed to open display", file=sys.stderr); sys.exit(1)
if out: print(out)
sys.exit(int(rc))
