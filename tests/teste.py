"""Testes da skill popup. Não abrem janela: usam zenity/kdialog/powershell falsos
(tests/bin); o WPF é simulado com popup.WINDOWS = True e confere o .ps1 gerado.

Rodar:  python3 tests/teste.py
"""
import json, os, subprocess, sys, tempfile
AQUI = os.path.dirname(os.path.abspath(__file__))
SK = os.path.join(os.path.dirname(AQUI), "skills", "popup")
BIN = os.path.join(AQUI, "bin")
FIXTURE_FAV = os.path.join(AQUI, "fixtures", "favoritas.txt")
S = tempfile.mkdtemp(prefix="popup-teste-")   # logs, filas, históricos, cópias
sys.path.insert(0, SK)
import textos as tx
falhas = []
def checa(nome, cond, info=""):
    print(("  ok   " if cond else "  FALHA ") + nome + ("" if cond else f"  → {info}"))
    if not cond: falhas.append(nome)

print("1. Escolha do idioma")
base = {k: v for k, v in os.environ.items()
        if k not in ("LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE", "POPUP_IDIOMA", "POPUP_LANG", "POPUP_BACKEND", "POPUP_FAVORITAS", "POPUP_ESTADO",
                     "POPUP_FAVORITES", "POPUP_STATE_DIR")}
# Nada de tocar a configuração real do usuário; e uma "tela" falsa para rodar em CI.
base["XDG_CONFIG_HOME"] = os.path.join(S, "config")
base["XDG_STATE_HOME"] = os.path.join(S, "state")
if not base.get("WAYLAND_DISPLAY") and not base.get("DISPLAY"):
    base["DISPLAY"] = ":99"
casos = [
    ({}, "en", None, "en", "--idioma en vence o sistema"),
    ({"LANG": "en_US.UTF-8"}, "pt-BR", None, "pt", "--idioma pt-BR → pt"),
    ({"LANG": "pt_BR.UTF-8", "POPUP_LANG": "es"}, "", None, "es", "POPUP_IDIOMA vence LANG"),
    ({"LANG": "pt_BR.UTF-8"}, "", None, "pt", "LANG pt_BR.UTF-8 → pt"),
    ({"LANG": "es_AR.UTF-8"}, "", None, "es", "LANG es_AR → es"),
    ({"LANGUAGE": "es:en", "LANG": "pt_BR.UTF-8"}, "", None, "es", "LANGUAGE vence LANG (igual gettext)"),
    ({"LC_ALL": "C"}, "", None, "en", "locale C → inglês"),
    ({"LANG": "ko_KR.UTF-8"}, "", None, "en", "LANG coreano (sem tradução) → inglês"),
    ({"LANG": "de_DE.UTF-8"}, "", None, "de", "LANG de_DE → de"),
    ({"LANG": "pt_BR.UTF-8"}, "ko", None, "en", "--idioma ko (sem tradução) → inglês, não o sistema"),
    ({"LANG": "pt_BR.UTF-8", "POPUP_LANG": "ar"}, "", None, "en", "POPUP_IDIOMA ar (sem tradução) → inglês"),
    ({}, "pt-PT", None, "pt-PT", "--idioma pt-PT → variante pt-PT"),
    ({"LANG": "pt_PT.UTF-8"}, "", None, "pt-PT", "LANG pt_PT → variante pt-PT"),
    ({}, "pt-BR", None, "pt", "--idioma pt-BR → pt"),
    ({"LANG": "ja_JP.UTF-8"}, "", None, "ja", "LANG ja_JP → ja"),
    ({}, "zh-CN", None, "zh", "--idioma zh-CN → zh"),
    ({}, "ru", None, "ru", "--idioma ru → ru"),
]
for env, pedido, _, esperado, nome in casos:
    os.environ.clear(); os.environ.update(base); os.environ.update(env)
    checa(nome, tx.resolver(pedido)[0] == esperado, tx.resolver(pedido))
os.environ.clear(); os.environ.update(base)
chaves = set(tx.TEXTOS["pt"])
checa(f"{len(tx.TEXTOS)} idiomas têm as mesmas chaves", all(set(v) == chaves for v in tx.TEXTOS.values()))
checa("pt-PT: 'prima Enter'", "prima Enter" in tx.TEXTOS["pt-PT"]["entrada"])
checa("contador formata em todos os idiomas", all(v["contador"].format(m=1, s=5) for v in tx.TEXTOS.values()))

def roda(args, fila, env_extra=None, desktop="GNOME"):
    log, resp = f"{S}/log.jsonl", f"{S}/fila.txt"
    open(log, "w").close(); open(resp, "w").write("\n".join(fila))
    env = dict(base, PATH=f"{BIN}:" + base["PATH"], FAKE_LOG=log, FAKE_RESP=resp,
               XDG_CURRENT_DESKTOP=desktop, LANG="pt_BR.UTF-8")
    import tempfile, shutil as _sh
    if "POPUP_STATE_DIR" not in (env_extra or {}):
        env["POPUP_STATE_DIR"] = tempfile.mkdtemp(dir=S)
    if "POPUP_FAVORITES" not in (env_extra or {}):
        env["POPUP_FAVORITES"] = f"{S}/fav-copia.txt"
        _sh.copyfile(FIXTURE_FAV, env["POPUP_FAVORITES"])
    env.update(env_extra or {})
    r = subprocess.run([f"{SK}/popup.py", *args], capture_output=True, text=True, env=env, timeout=30)
    chamadas = [json.loads(l) for l in open(log) if l.strip()]
    return r.returncode, r.stdout.strip(), r.stderr, chamadas

C = ["--greeting", "Ei", "--question", "Qual?", "--timeout", "30"]
O = ["--option", "🧩|Opção A|faz A", "--option", "🚀|Opção B|faz B"]

print("2. zenity falso")
cod, out, err, ch = roda(["yesno", "--backend", "zenity", "--lang", "en", *C], ["0|"])
a = ch[0]["argv"]
checa("simnao en: botões Yes/No", "--ok-label=👍 Yes" in a and "--cancel-label=👎 No" in a, a)
checa("simnao en: saída continua 'sim', exit 0", (cod, out) == (0, "yes"), (cod, out))
cod, out, err, ch = roda(["yesno", "--backend", "zenity", *C], ["1|"], {"POPUP_AGENTE": ""})
checa("sem --idioma usa LANG=pt_BR: botão Sim", "--ok-label=👍 Sim" in ch[0]["argv"], ch[0]["argv"])
checa("simnao 'Não': saída 'não', exit 1", (cod, out) == (1, "no"), (cod, out))
cod, out, err, ch = roda(["ask", "--backend", "zenity", "--lang", "es", *C, *O],
                         ["0|✏️  Escribir otra respuesta…", "0|mi respuesta"])
a1, a2 = ch[0]["argv"], ch[1]["argv"]
checa("pergunta es: linha 'Escribir otra respuesta…'", "✏️  Escribir otra respuesta…" in a1, a1)
checa("pergunta es: botões Elegir / Ahora no", "--ok-label=Elegir" in a1 and "--cancel-label=Ahora no" in a1, a1)
checa("pergunta es: 2ª janela Responder/Ahora no", "--ok-label=Responder" in a2 and "--cancel-label=Ahora no" in a2, a2)
checa("pergunta es: resposta escrita volta no stdout", (cod, out) == (0, "mi respuesta"), (cod, out))
cod, out, err, ch = roda(["ask", "--backend", "zenity", "--lang", "pt", *C, *O], ["0|🚀  Opção B — faz B"])
checa("pergunta pt: escolher cartão devolve o título", (cod, out) == (0, "Opção B"), (cod, out))
cod, out, err, ch = roda(["terminal", "--backend", "zenity", "--lang", "en", *C], ["5|"])
checa("terminal en: botão 'On my way!'", "--ok-label=🏃 On my way!" in ch[0]["argv"], ch[0]["argv"])
checa("timeout do zenity vira exit 5", cod == 5, cod)
cod, out, err, ch = roda(["yesno", "--lang", "en", *C], ["0|<FALHA_TELA>", "0|"], desktop="GNOME",
                         env_extra={"POPUP_BACKEND": "zenity,kdialog"})
checa("zenity sem tela → passa para kdialog", [c["prog"] for c in ch] == ["zenity", "kdialog"] and cod == 0,
      ([c["prog"] for c in ch], cod, err))

print("3. kdialog falso (desktop KDE)")
cod, out, err, ch = roda(["ask", "--lang", "en", *C, *O], ["0|outra", "0|typed answer"], desktop="KDE")
checa("KDE escolhe kdialog primeiro", ch and ch[0]["prog"] == "kdialog", ch[:1])
a1 = ch[0]["argv"]
checa("menu en tem 'Write another answer…'", "✏️  Write another answer…" in a1, a1)
checa("'outra' abre inputbox e devolve o texto", ch[1]["argv"][2] == "--inputbox" and (cod, out) == (0, "typed answer"),
      (ch[1]["argv"], cod, out))
cod, out, err, ch = roda(["yesno", "--lang", "es", *C], ["0|"], desktop="KDE")
checa("simnao es: Sí / No", "👍 Sí" in ch[0]["argv"] and "👎 No" in ch[0]["argv"], ch[0]["argv"])
cod, out, err, ch = roda(["ask", "--lang", "pt", *C, *O], ["0|1"], desktop="KDE")
checa("menu tag 1 devolve 'Opção A'", (cod, out) == (0, "Opção A"), (cod, out))

print("4. diagnostico")
for env, esp in (({"LANG": "es_ES.UTF-8"}, "language: es (from system (es_ES.UTF-8))"),
                 ({"POPUP_LANG": "en"}, "language: en (from POPUP_LANG)")):
    r = subprocess.run([f"{SK}/popup.py", "doctor"], capture_output=True, text=True, env=dict(base, **env))
    checa(f"diagnostico mostra '{esp}'", esp in r.stdout, r.stdout)

print("5. Favoritas e histórico (zenity falso)")
import tempfile, shutil, time as _t
FAV = f"{S}/fav-teste.txt"
def novo_estado():
    shutil.copyfile(FIXTURE_FAV, FAV)
    return {"POPUP_STATE_DIR": tempfile.mkdtemp(dir=S), "POPUP_FAVORITES": FAV}
F1 = "Chefia, me ajuda numa decisão rapidinha?"
F2 = "Ô parceiro, empaquei numa escolha. Me ajuda?"
def sn(chamada, idioma, env, fila=("0|",), **kw):
    return roda(["yesno", "--backend", "zenity", "--lang", idioma, "--greeting", chamada,
                 "--question", "P?", "--timeout", "30"], list(fila), env, **kw)
e = novo_estado()
cod, out, err, ch = sn(F1, "pt-BR", e); checa("1ª favorita pt-BR abre", cod == 0 and len(ch) == 1, (cod, err))
cod, out, err, ch = sn(F2, "pt-BR", e); checa("2ª favorita seguida → exit 7, sem janela", cod == 7 and not ch, (cod, ch))
checa("motivo explicado no stderr", "favorite" in err and "run again" in err, err)
cod, out, err, ch = sn("Tem um minutinho pra mim?", "pt-BR", e); checa("chamada nova abre", cod == 0, (cod, err))
cod, out, err, ch = sn(F2, "pt-BR", e); checa("favorita depois de chamada nova abre", cod == 0, (cod, err))
cod, out, err, ch = sn(F1, "pt-BR", e); checa("favorita já usada → exit 7", cod == 7 and "already used" in err, (cod, err))
cod, out, err, ch = sn("  tem UM minutinho   pra mim? ", "pt-BR", e)
checa("chamada nova repetida (maiúsculas/espaços) → exit 7", cod == 7, (cod, err))
cod, out, err, ch = sn(F1, "pt", novo_estado()); checa("--idioma pt equivale a pt-BR", cod == 0, (cod, err))
cod, out, err, ch = sn(F1, "pt-PT", novo_estado()); checa("favorita pt-BR em conversa pt-PT → exit 7", cod == 7 and "pt-BR" in err, (cod, err))
cod, out, err, ch = sn(F1, "en", novo_estado()); checa("favorita pt-BR em conversa en → exit 7", cod == 7, (cod, err))
e = novo_estado()
cod, out, err, ch = sn(F1, "pt-BR", e, env_extra=None) if False else (None,)*4
cod, out, err, ch = roda(["yesno", "--lang", "pt-BR", "--greeting", F1, "--question", "P?"], [], dict(e, WAYLAND_DISPLAY="", DISPLAY=""))
checa("sem tela (exit 6) não entra no histórico", cod == 6, cod)
cod, out, err, ch = sn(F1, "pt-BR", e); checa("…então a mesma chamada abre depois", cod == 0, (cod, err))
est = f"{e['POPUP_STATE_DIR']}/historico.json"
import json as _j
d = _j.load(open(est)); [i.update(t=i["t"] - 3*3600) for v in d.values() for i in v]; _j.dump(d, open(est, "w"))
cod, out, err, ch = sn(F1, "pt-BR", e); checa("depois de 2 h sem pop-up a tarefa recomeça", cod == 0, (cod, err))

print("6. Comando favorita")
e = novo_estado()
def fv(*args):
    r = subprocess.run([f"{SK}/popup.py", "favorite", *args], capture_output=True, text=True, env=dict(base, **e))
    return r.returncode, r.stdout.strip()
cod, out = fv("add", "--lang", "ja", "ちょっといいですか？"); checa("add cria a seção [ja]", cod == 0 and "[ja]" in out and "[ja]\nちょっといいですか？" in open(FAV).read(), (cod, out))
cod, out = fv("add", "--lang", "ja-JP", "ちょっといいですか？"); checa("add repetido (ja-JP = ja) → 'já estava'", "already in" in out, out)
cod, out = fv("add", "--lang", "pt-BR", "Mestre, me dá uma luz aqui?")
txt = open(FAV).read()
checa("add pt-BR entra no fim da seção [pt-BR], antes de [ja]", txt.index("Mestre") < txt.index("\n[ja]\n") and txt.index("Ô parceiro") < txt.index("Mestre"), txt)
checa("comentários do arquivo preservados", txt.startswith("# Chamadas favoritas"), txt[:60])
cod, out = fv("list", "--lang", "ja"); checa("list --idioma ja mostra só [ja]", "[ja]" in out and "[pt-BR]" not in out, out)
cod, out = fv("rm", "--lang", "pt-BR", "Mestre, me dá uma luz aqui?"); checa("rm tira", cod == 0 and "Mestre" not in open(FAV).read(), (cod, out))
cod, out = fv("rm", "--lang", "pt-BR", "Mestre, me dá uma luz aqui?"); checa("rm de algo que não está → exit 1", cod == 1, (cod, out))
cod, out = fv("add", "--lang", "es", "¿Me das una mano con esto?")
cod, out, err, ch = sn("¿Me das una mano con esto?", "es-MX", e); checa("es-MX usa favoritas de [es]", cod == 0, (cod, err))
r = subprocess.run([f"{SK}/popup.py", "favorite", "add", "sem idioma"], capture_output=True, text=True, env=dict(base, **e, LANG="pt_BR.UTF-8"))
checa("add sem --idioma dá erro", r.returncode != 0, r.returncode)

print("7. Arquivo de favoritas novo")
os.remove(FAV)
cod, out = fv("add", "--lang", "en", "Hey, can you help me?")
txt = open(FAV).read()
checa("arquivo novo nasce do favoritas.exemplo.txt", "[en]\nHey, can you help me?" in txt and "[pt-BR]" in txt, txt[-200:])
d = os.path.join(S, "cfg-vazio")
r = subprocess.run([f"{SK}/popup.py", "favorite", "add", "--lang", "es", "¿Me ayudas?"], capture_output=True, text=True,
                   env={k: v for k, v in dict(base, XDG_CONFIG_HOME=d).items() if k != "POPUP_FAVORITES"})
checa("sem POPUP_FAVORITES grava em XDG_CONFIG_HOME/popup/favorites.txt", os.path.exists(f"{d}/popup/favorites.txt"), r.stderr)

print("8. Nomes antigos (0.1) continuam funcionando")
cod, out, err, ch = roda(["simnao", "--backend", "zenity", "--idioma", "en", "--chamada", "Old?",
                          "--pergunta", "Q?", "--timeout", "30"], ["0|"])
checa("simnao/--chamada/--pergunta/--idioma: abre com botão Yes e sai 'yes'",
      (cod, out) == (0, "yes") and "--ok-label=👍 Yes" in ch[0]["argv"], (cod, out, err))
cod, out, err, ch = roda(["pergunta", "--backend", "zenity", "--idioma", "es", "--chamada", "Vieja",
                          "--pergunta", "Q?", "--opcao", "🧩|Uno|a", "--sem-outra", "--contexto", "c"],
                         ["0|🧩  Uno — a"])
checa("pergunta/--opcao/--sem-outra/--contexto funcionam", (cod, out) == (0, "Uno") and "Escribir" not in str(ch), (cod, out, err))
r = subprocess.run([f"{SK}/popup.py", "diagnostico"], capture_output=True, text=True, env=dict(base, POPUP_IDIOMA="ja"))
checa("diagnostico + POPUP_IDIOMA (apelido) funcionam", "language: ja" in r.stdout, r.stdout + r.stderr)
r = subprocess.run([f"{SK}/popup.py", "--help"], capture_output=True, text=True, env=base)
checa("--help não mostra os apelidos", "--chamada" not in r.stdout and "pergunta" not in r.stdout and "--greeting" in r.stdout, r.stdout)
d = os.path.join(S, "migra")
os.makedirs(f"{d}/popup"); open(f"{d}/popup/favoritas.txt", "w").write("[pt-BR]\nFrase antiga\n")
r = subprocess.run([f"{SK}/popup.py", "favorite", "list"], capture_output=True, text=True,
                   env={k: v for k, v in dict(base, XDG_CONFIG_HOME=d).items() if k not in ("POPUP_FAVORITES",)})
checa("favoritas.txt da 0.1 vira favorites.txt no primeiro uso",
      os.path.exists(f"{d}/popup/favorites.txt") and not os.path.exists(f"{d}/popup/favoritas.txt") and "Frase antiga" in r.stdout,
      (os.listdir(f"{d}/popup"), r.stdout, r.stderr))
# nomes novos vazios = não definidos; só os apelidos valem
e2 = {"POPUP_FAVORITES": "", "POPUP_STATE_DIR": "",
      "POPUP_FAVORITAS": FIXTURE_FAV, "POPUP_ESTADO": tempfile.mkdtemp(dir=S)}
cod, out, err, ch = roda(["yesno", "--backend", "zenity", "--lang", "pt-BR", "--greeting", "Chefia, me ajuda numa decisão rapidinha?",
                          "--question", "Q?"], ["0|"], e2)
cod2, out2, err2, ch2 = roda(["yesno", "--backend", "zenity", "--lang", "pt-BR", "--greeting", "Ô parceiro, empaquei numa escolha. Me ajuda?",
                              "--question", "Q?"], ["0|"], e2)
checa("POPUP_FAVORITAS/POPUP_ESTADO (apelidos) valem: 2ª favorita seguida → 7", (cod, cod2) == (0, 7), (cod, cod2, err2))

print("9. WSL: janela nativa do Windows pelo powershell.exe (falso)")
WSL = {"WSL_DISTRO_NAME": "Ubuntu-Teste", "DISPLAY": "", "WAYLAND_DISPLAY": ""}
r = subprocess.run([f"{SK}/popup.py", "doctor"], capture_output=True, text=True,
                   env=dict(base, PATH=f"{BIN}:" + base["PATH"], **WSL))
checa("doctor no WSL: 'wsl: yes', powershell primeiro e escolhido",
      "wsl: yes" in r.stdout and "order: powershell, gtk" in r.stdout and "chosen: powershell" in r.stdout, r.stdout)
OPS = ["--option", "🧩|Opción A|hace A", "--option", "🚀|Opción B|hace B"]
cod, out, err, ch = roda(["ask", "--lang", "es", "--greeting", "Oye, ¿me ayudas?", "--question", "¿Cuál?",
                          "--context", "ctx", *OPS], ["0|Opción B"], WSL)
d = ch[0].get("dados") if ch else {}
checa("ask no WSL sem tela X: abre no Windows e devolve a opção", (cod, out) == (0, "Opción B") and ch and ch[0]["prog"] == "powershell.exe", (cod, out, err))
checa("script com dados embutidos e trap de erro", ch and ch[0]["script_ok"] and ch[0]["trap"], ch[:1])
checa("dados: modo, textos em es, opções e contador", d and d["modo"] == "pergunta" and d["t"]["agora_nao"] == "Ahora no"
      and [o["valor"] for o in d["opcoes"]] == ["Opción A", "Opción B"] and d["cpre"] == "se cierra en " and d["contexto"] == "ctx", d)
checa("sem arquivo temporário: usa -EncodedCommand, não -File", ch and "-EncodedCommand" in ch[0]["flags"] and "-File" not in ch[0]["flags"] and "-STA" in ch[0]["flags"], ch[:1])
cod, out, err, ch = roda(["yesno", "--lang", "pt-BR", "--greeting", "G1?", "--question", "Q?"], ["0|yes"], WSL)
checa("yesno no WSL → yes, exit 0", (cod, out) == (0, "yes") and ch[0]["dados"]["t"]["sim"] == "Sim", (cod, out, err))
cod, out, err, ch = roda(["yesno", "--lang", "en", "--greeting", "G2?", "--question", "Q?"], ["1|no"], WSL)
checa("yesno no WSL → no, exit 1", (cod, out) == (1, "no"), (cod, out, err))
cod, out, err, ch = roda(["terminal", "--lang", "ja", "--greeting", "G3?", "--question", "Q?"], ["5|"], WSL)
checa("timeout do PowerShell vira exit 5", cod == 5 and ch[0]["dados"]["t"]["ja_vou"] == "今行きます！", (cod, err))
cod, out, err, ch = roda(["yesno", "--lang", "en", "--greeting", "G4?", "--question", "Q?"], ["3|"], WSL)
checa("erro no PowerShell (exit 3) sem tela X → exit 6", cod == 6 and "powershell failed" in err, (cod, err))
cod, out, err, ch = roda(["yesno", "--lang", "en", "--greeting", "G5?", "--question", "Q?"], ["3|", "0|"],
                         dict(WSL, DISPLAY=":99"))
checa("erro no PowerShell com WSLg → cai para o zenity", cod == 0 and [c["prog"] for c in ch] == ["powershell.exe", "zenity"], (cod, [c["prog"] for c in ch], err))
cod, out, err, ch = roda(["ask", "--lang", "en", "--greeting", "G6?", "--question", "Q?",
                          "--option", "📦|" + "x" * 40000 + "|grande"], ["0|x"], WSL)
checa("pergunta grande demais para a linha de comando → não chama o PowerShell", cod == 6 and not ch, (cod, ch[:1], err))
cod, out, err, ch = roda(["yesno", "--backend", "powershell", "--lang", "en", "--greeting", "G7?", "--question", "Q?"], ["0|yes"])
checa("Linux fora do WSL não usa powershell.exe", cod == 6 and not ch, (cod, [c["prog"] for c in ch]))
cod, out, err, ch = roda(["ask", "--lang", "pt-BR", "--greeting", "Oi! ⭐ Me dá uma mão? 🙌", "--question", "Qual ✏️ estilo?",
                          "--context", "⏳ rapidinho", "--option", "🎯|Só um pop-up|Fecha depois ✅",
                          "--option", "🙋‍♂️|Mais um|Abre outro", "--option", "1️⃣|Chamada ao terminal|Mostra o fluxo"], ["0|Mais um"], WSL)
d = ch[0]["dados"] if ch else {}
checa("janela do Windows mantém os emoji (vão em Segoe UI Emoji)",
      d and [o["rotulo"] for o in d["opcoes"]] == ["🎯  Só um pop-up — Fecha depois ✅", "🙋‍♂️  Mais um — Abre outro", "1️⃣  Chamada ao terminal — Mostra o fluxo"]
      and d["chamada"] == "Oi! ⭐ Me dá uma mão? 🙌" and d["pergunta"] == "Qual ✏️ estilo?" and d["contexto"] == "⏳ rapidinho", d)
checa("script do Windows troca a fonte quando o texto tem emoji",
      ch and "Segoe UI Emoji" in ch[0]["script"] and "FonteTexto" in ch[0]["script"]
      and "IsStyleAvailable" in ch[0]["script"], (ch[0].get("script", "")[:80] if ch else None))
checa("título mantém o ✨ e a resposta é o título original", d and d["titulo"].startswith("✨") and (cod, out) == (0, "Mais um"), (d.get("titulo"), cod, out))
sys.path.insert(0, SK); import popup as _pp
checa("tirar_emoji: acentos, CJK e símbolos comuns ficam", _pp.tirar_emoji("Ação ñ ü 中文 日本語 — © → ok") == "Ação ñ ü 中文 日本語 — © → ok", _pp.tirar_emoji("Ação ñ ü 中文 日本語 — © → ok"))

e9 = dict(WSL, POPUP_STATE_DIR=tempfile.mkdtemp(dir=S))
roda(["yesno", "--lang", "en", "--greeting", "Same one?", "--question", "Q?"], ["0|yes"], e9)
cod, out, err, ch = roda(["yesno", "--lang", "en", "--greeting", "Same one?", "--question", "Q?"], ["0|yes"], e9)
checa("histórico vale no WSL: chamada repetida → 7", cod == 7 and not ch, (cod, err))

print("10. Windows nativo: interface WPF")
import argparse, base64, re
from xml.etree import ElementTree as ET
import wpf as _wpf

def alvo(**kw):
    campos = dict(modo="pergunta", chamada="Chamada ✨", pergunta="Qual?", contexto="ctx",
                  timeout=300, sem_outra=False, opcao=["🧩|A|faz A"], idioma="es", idioma_fav="es")
    campos.update(kw)
    return argparse.Namespace(**campos)

def textos_do_script(s):
    saida = []
    for b in re.findall(r"FromBase64String\('([^']*)'\)", s):
        try:
            saida.append(base64.b64decode(b).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            pass
    return saida

def xaml_do_script(s):
    return next(t for t in textos_do_script(s) if t.lstrip().startswith("<"))

def dados_do_script(s):
    return json.loads(next(t for t in textos_do_script(s) if t.lstrip().startswith("{")))

d = _wpf.dados(alvo(titulo="✨ Agente · repo"))
checa("WPF dados: título, modo, textos e timeout",
      d["titulo"] == "✨ Agente · repo" and d["modo"] == "pergunta" and d["chamada"] == "Chamada ✨"
      and d["pergunta"] == "Qual?" and d["contexto"] == "ctx" and d["timeout"] == 300
      and d["sem_outra"] is False and d["t"]["agora_nao"] == "Ahora no", d)
checa("WPF dados: opção com emoji, título, descrição, valor e tecla",
      d["opcoes"] == [{"emoji": "🧩", "titulo": "A", "desc": "faz A", "valor": "A", "tecla": 1}],
      d["opcoes"])
checa("WPF dados: contador es sem o emoji",
      (d["cpre"], d["cpos"]) == ("se cierra en ", " · Esc cierra"), (d["cpre"], d["cpos"]))
d = _wpf.dados(alvo(idioma="pt", idioma_fav="pt-BR", sem_outra=True,
                    opcao=["sem emoji", "👉|B|"]), titulo="T")
checa("WPF dados: opção sem 'emoji|' ganha 👉 e descrição vazia",
      [o["emoji"] for o in d["opcoes"]] == ["👉", "👉"] and d["opcoes"][0]["valor"] == "sem emoji"
      and d["opcoes"][1]["desc"] == "", d["opcoes"])
checa("WPF dados: contador pt e sem_outra",
      d["cpre"] == "fecha sozinho em " and d["cpos"] == " · Esc fecha" and d["sem_outra"], d)

s = _wpf.script(alvo(titulo="✨ Agente · repo",
                     opcao=["🧩|Ação & <b>|faz \"A\"", "🚀|B|faz B"]), r"C:\popup\assets\wpf")
checa("WPF script: dados e XAML embutidos, sem marcadores",
      "__DADOS_B64__" not in s and "__XAML_B64__" not in s and "__ASSETS__" not in s
      and "ShowDialog" in s and s.lstrip().splitlines()[1].startswith("trap"), s[:120])
checa("WPF script: dados conferem com dados()",
      dados_do_script(s)["chamada"] == "Chamada ✨" and dados_do_script(s)["opcoes"][1]["valor"] == "B",
      dados_do_script(s))
x = xaml_do_script(s)
checa("WPF XAML: título, chamada, pergunta, contexto e selo",
      'Title="✨ Agente · repo"' in x and "Chamada ✨" in x and "Qual?" in x and "ctx" in x
      and "PREGUNTA RÁPIDA" in x, x[:200])
checa("WPF XAML: cartões com emoji, texto e tecla 1..9",
      "🧩" in x and "Ação &amp; &lt;b&gt;" in x and "faz &quot;A&quot;" in x and 'Text="1"' in x
      and 'Text="2"' in x, x)
checa("WPF XAML: campo de resposta e botões Agora não/Responder",
      'x:Name="entrada"' in x and "Ahora no" in x and "Responder" in x, x)
e = ET.fromstring(x)
checa("WPF XAML: XML válido com emoji, &, <, aspas e quebra de linha",
      e is not None and "&#10;" in xaml_do_script(
          _wpf.script(alvo(pergunta="linha 1\nlinha 2"), "/tmp/a")), "XML inválido")
checa("WPF script: tema automático com tokens e as duas paletas",
      "AppsUseLightTheme" in s and "__BG__" in x and "__CARD_BG__" in x
      and "#242424" in s and "#FAFAFA" in s and "ValidateSet('auto', 'light', 'dark')" in s, s[:80])
ordem_dll = ["Stfu.dll", "Typography.OpenFont.dll", "Typography.GlyphLayout.dll", "Emoji.Wpf.dll"]
pos = [s.index(n) for n in ordem_dll]
checa("WPF script: DLLs carregadas na ordem (Stfu antes de Emoji.Wpf)", pos == sorted(pos), pos)
codificado = len(base64.b64encode(s.encode("utf-16-le")))
checa("WPF script: caminho dos assets e grande demais para -EncodedCommand",
      r"C:\popup\assets\wpf" in s and codificado > 32767, (r"C:\popup\assets\wpf" in s, len(s), codificado))
checa("WPF script: estrela grava o controle e usa as dicas do idioma",
      "estrelaTexto" in s and "WriteAllText" in s and "fav_salva" in s and "$d.controle" in s, "")
s = _wpf.script(alvo(modo="pergunta", sem_outra=True), "/tmp/assets")
x = xaml_do_script(s)
checa("WPF sem_outra: sem campo de resposta e sem Responder",
      'x:Name="entrada"' not in x and "Ahora no" in x and "Responder" not in x, x)
x = xaml_do_script(_wpf.script(alvo(modo="simnao"), "/tmp/assets"))
checa("WPF simnao: botões Não/Sim e sem cartões",
      'x:Name="naoBtn"' in x and 'x:Name="simBtn"' in x and 'x:Name="opcoes"' in x
      and "🧩" not in x, x)
x = xaml_do_script(_wpf.script(alvo(modo="terminal", idioma="ja"), "/tmp/assets"))
checa("WPF terminal: botão Já vou!", 'x:Name="jaVou"' in x and "今行きます！" in x, x)

def roda_win(args, fila, env_extra=None, pre="", path=None):
    """Roda popup.py como no Windows nativo (popup.WINDOWS=True), sem janela de verdade."""
    launcher = f"{S}/roda_win.py"
    with open(launcher, "w") as f:
        f.write("import sys\n"
                f"sys.path.insert(0, {SK!r})\nimport popup\npopup.WINDOWS = True\n{pre}\n"
                "sys.argv = ['popup.py'] + sys.argv[1:]\npopup.main()\n")
    log, resp = f"{S}/log.jsonl", f"{S}/fila.txt"
    open(log, "w").close(); open(resp, "w").write("\n".join(fila))
    env = dict(base, PATH=f"{BIN}:" + base["PATH"], FAKE_LOG=log, FAKE_RESP=resp,
               LANG="en_US.UTF-8", POPUP_STATE_DIR=tempfile.mkdtemp(dir=S),
               POPUP_FAVORITES=f"{S}/fav-copia.txt")
    shutil.copyfile(FIXTURE_FAV, env["POPUP_FAVORITES"])
    env.update(env_extra or {})
    if path:
        env["PATH"] = path
    r = subprocess.run([sys.executable, launcher, *args], capture_output=True, text=True, env=env, timeout=30)
    chamadas = [json.loads(l) for l in open(log) if l.strip()]
    return r.returncode, r.stdout.strip(), r.stderr, chamadas

cod, out, err, ch = roda_win(["doctor"], [])
checa("doctor no Windows: ordem wpf, tkinter, powershell e wpf escolhido",
      "order: wpf, tkinter, powershell" in out and "chosen: wpf" in out
      and re.search(r"wpf\s+✓", out), out)
cod, out, err, ch = roda_win(["ask", "--lang", "es", "--greeting", "Oye ✨", "--question", "¿Cuál?",
                              "--context", "ctx", "--option", "🧩|Opción A|hace A",
                              "--option", "🚀|Opción B|hace B"], ["0|Opción B"])
d = ch[0]["dados"] if ch else {}
checa("Windows ask: abre o WPF, devolve a opção e sai 0",
      (cod, out) == (0, "Opción B") and ch and ch[0]["forma"] == "file", (cod, out, err, ch[:1]))
checa("Windows ask: -File UTF-8 BOM, -STA, sem -EncodedCommand",
      ch and ch[0]["bom"] and "-File" in ch[0]["flags"] and "-STA" in ch[0]["flags"]
      and "-EncodedCommand" not in ch[0]["flags"], ch[:1])
checa("Windows ask: dados com modo, textos em es e opções",
      d and d["modo"] == "pergunta" and d["t"]["agora_nao"] == "Ahora no"
      and [o["valor"] for o in d["opcoes"]] == ["Opción A", "Opción B"]
      and d["cpre"] == "se cierra en " and d["contexto"] == "ctx", d)
checa("Windows ask: XAML com chamada, opções e caminho dos assets no script",
      ch and "Oye ✨" in ch[0]["xaml"] and "Opción B" in ch[0]["xaml"]
      and "/assets/wpf" in ch[0]["script"], (ch[0].get("xaml", "")[:200] if ch else None))
checa("Windows ask: script pronto e arquivo temporário apagado",
      ch and ch[0]["script_ok"] and ch[0]["trap"] and not os.path.exists(ch[0]["caminho"]), ch[:1])
checa("Windows ask: controle da estrela em arquivo temporário",
      d and d["favorita"] is False and d["controle"].endswith("favorita"), d)
cod, out, err, ch = roda_win(["yesno", "--lang", "pt-BR", "--greeting", "G?",
                              "--question", "Q?"], ["0|yes"])
x = ch[0]["xaml"] if ch else ""
checa("Windows yesno: Sim/Não e saída yes",
      (cod, out) == (0, "yes") and 'x:Name="simBtn"' in x and "Sim" in x and "Não" in x, (cod, out, err))
cod, out, err, ch = roda_win(["terminal", "--lang", "ja", "--greeting", "G?", "--question", "Q?"], ["5|"])
checa("Windows terminal: timeout vira exit 5", cod == 5 and ch and ch[0]["dados"]["timeout"] == 300,
      (cod, err))
cod, out, err, ch = roda_win(["yesno", "--lang", "en", "--greeting", "G?", "--question", "Q?",
                              "--backend", "wpf,powershell"], ["0|yes"],
                             pre="import wpf\nwpf.PASTA = '/nao-existe'")
checa("sem DLLs do WPF: cai para o WinForms (fallback)",
      cod == 0 and ch and ch[0]["forma"] == "encoded", (cod, [c["forma"] for c in ch], err))
cod, out, err, ch = roda_win(["yesno", "--lang", "en", "--greeting", "G?", "--question", "Q?",
                              "--backend", "wpf"], ["0|yes"], path="/usr/bin:/bin")
checa("sem powershell no PATH: WPF indisponível, exit 6, sem janela",
      cod == 6 and not ch, (cod, ch[:1], err))
cod, out, err, ch = roda_win(["doctor"], [], pre="import wpf\nwpf.PASTA = '/nao-existe'")
linhas = [l for l in out.splitlines() if l.strip().startswith("wpf")]
checa("doctor com DLLs ausentes marca wpf ✗",
      bool(linhas) and "✗" in linhas[0], out)
cod, out, err, ch = roda_win(["doctor"], [])
linhas = [l for l in out.splitlines() if l.strip().startswith("wpf")]
checa("doctor mostra wpf", bool(linhas) and "✓" in linhas[0], out)
cod, out, err, ch = roda(["yesno", "--backend", "wpf", "--lang", "en", *C], ["0|yes"])
checa("Linux (fora do WSL) não usa WPF", cod == 6 and not ch, (cod, ch[:1], err))

print("11. WPF: favorita pela estrela")
os.environ["POPUP_FAVORITES"] = FIXTURE_FAV
try:
    checa("WPF dados: estrela marcada quando a chamada já é favorita",
          _wpf.dados(alvo(chamada=F1, idioma="pt-BR", idioma_fav="pt-BR", titulo="T"))["favorita"] is True)
    checa("WPF dados: estrela vazia para chamada nova",
          _wpf.dados(alvo(chamada="Nova chamada", idioma="pt-BR", idioma_fav="pt-BR", titulo="T"))["favorita"] is False)
finally:
    os.environ.pop("POPUP_FAVORITES", None)
e = novo_estado()
os.environ["POPUP_FAVORITES"] = e["POPUP_FAVORITES"]
try:
    a_fav = alvo(chamada="Nova favorita da estrela", idioma="pt-BR", idioma_fav="pt-BR")
    controle = f"{S}/controle-estrela"
    open(controle, "w").write("1")
    r = _wpf.aplicar_favorita(a_fav, controle)
    checa("estrela: '1' grava a chamada nas favoritas",
          r is True and "Nova favorita da estrela" in open(e["POPUP_FAVORITES"]).read(), r)
    open(controle, "w").write("0")
    r = _wpf.aplicar_favorita(a_fav, controle)
    checa("estrela: '0' tira a chamada das favoritas",
          r is False and "Nova favorita da estrela" not in open(e["POPUP_FAVORITES"]).read(), r)
    checa("estrela: sem clique (sem arquivo) não mexe",
          _wpf.aplicar_favorita(a_fav, f"{S}/nao-existe") is None
          and "Nova favorita da estrela" not in open(e["POPUP_FAVORITES"]).read())
finally:
    os.environ.pop("POPUP_FAVORITES", None)

print("12. Preferências de apresentação")
import preferencias as pref
arq = f"{S}/prefs.txt"
os.environ["POPUP_PREFERENCES"] = arq
os.environ.pop("POPUP_MODE", None); os.environ.pop("POPUP_MODO", None)
if os.path.exists(arq): os.unlink(arq)
checa("preferência: padrão window", pref.modo() == "window" and pref.origem() == "default")
checa("preferência: grava dialog", pref.gravar("dialog") == "dialog" and "mode = dialog" in open(arq).read())
checa("preferência: lê o arquivo", pref.modo() == "dialog" and pref.origem() == "file")
os.environ["POPUP_MODE"] = "notification"
checa("preferência: POPUP_MODE vence o arquivo", pref.modo() == "notification" and pref.origem() == "env")
checa("preferência: --mode vence POPUP_MODE", pref.modo("window") == "window" and pref.origem("window") == "flag")
os.environ.pop("POPUP_MODE")
try:
    pref.gravar("barra"); invalido = False
except ValueError:
    invalido = True
checa("preferência: valor inválido é recusado", invalido)
os.environ.pop("POPUP_PREFERENCES", None)

cod, out, err, ch = roda(["preference"], [], env_extra={"POPUP_PREFERENCES": arq})
checa("CLI preference: imprime o modo do arquivo", (cod, out) == (0, "dialog"), (cod, out, err))
cod, out, err, ch = roda(["preference", "list"], [], env_extra={"POPUP_PREFERENCES": arq})
checa("CLI preference list: modo, origem e arquivo",
      cod == 0 and "mode: dialog" in out and "source: file" in out and arq in out, (out, err))
cod, out, err, ch = roda(["preference", "set", "window"], [], env_extra={"POPUP_PREFERENCES": arq})
checa("CLI preference set: grava e imprime",
      cod == 0 and "mode: window" in out and "mode = window" in open(arq).read(), (out, err))
cod, out, err, ch = roda(["preference", "set", "dialog"],
                         [], env_extra={"POPUP_PREFERENCES": arq, "POPUP_MODE": "notification"})
checa("CLI preference set: avisa que POPUP_MODE vence",
      cod == 0 and ("POPUP_MODE" in err or "source: env" in out), (out, err))

print("13. Modo notification")
cod, out, err, ch = roda(["ask", "--lang", "en", "--greeting", "G?", "--question", "Q?",
                          "--mode", "notification"], [])
checa("notification: ask sai 6 sem abrir janela", cod == 6 and not ch, (cod, ch, err))
cod, out, err, ch = roda(["yesno", "--lang", "en", "--greeting", "G?", "--question", "Q?",
                          "--mode", "notification"], [])
checa("notification: yesno sai 6 sem abrir janela", cod == 6 and not ch, (cod, ch, err))
cod, out, err, ch = roda(["notify", "--lang", "pt-BR", "--greeting", "Terminei",
                          "--mode", "notification"], ["0|"])
checa("notification: notify envia urgency normal",
      cod == 0 and ch and ch[0]["prog"] == "notify-send"
      and "--urgency=normal" in ch[0]["argv"], (cod, ch, err))
cod, out, err, ch = roda(["terminal", "--lang", "pt-BR", "--greeting", "Terminei",
                          "--question", "Q?", "--mode", "notification"], ["0|"])
checa("notification: terminal envia urgency critical",
      cod == 0 and ch and "--urgency=critical" in ch[0]["argv"], (cod, ch, err))
cod, out, err, ch = roda(["notify", "--lang", "pt-BR", "--greeting", "Terminei",
                          "--mode", "notification"], ["1|"])
checa("notification: falha do notificador sai 6", cod == 6 and "notification" in err, (cod, err))

print("14. notify em window/dialog")
cod, out, err, ch = roda(["notify", "--lang", "pt-BR", "--greeting", "Terminei",
                          "--backend", "zenity"], ["0|"])
checa("notify window: zenity com botão OK e exit 0",
      cod == 0 and ch and "--ok-label=OK" in ch[0]["argv"], (cod, ch, err))
cod, out, err, ch = roda(["notify", "--lang", "pt-BR", "--greeting", "Terminei",
                          "--backend", "zenity"], ["5|"])
checa("notify window: timeout vira exit 0", cod == 0, (cod, err))

print("15. Apresentação dialog")
import popup
visto = {}
def rodar_falso(cmd, timeout):
    visto["cmd"] = cmd
    return 0, "ok", ""
original = popup.rodar
popup.rodar = rodar_falso
try:
    popup.ui_gtk(alvo(modo="notify", chamada="G", pergunta="", contexto="",
                      timeout=20, opcao=[], sem_outra=False, idioma_fav="en",
                      apresentacao="dialog"))
finally:
    popup.rodar = original
cmd = visto.get("cmd") or []
checa("GTK dialog: --apresentacao dialog no comando",
      "--apresentacao" in cmd and cmd[cmd.index("--apresentacao") + 1] == "dialog", cmd)

cod, out, err, ch = roda_win(["notify", "--lang", "en", "--greeting", "Done"], ["0|ok"])
x = ch[0]["xaml"] if ch else ""
checa("Windows notify: selo, botão OK e exit 0",
      cod == 0 and out == "ok" and 'x:Name="okBtn"' in x and "TASK COMPLETED" in x,
      (cod, out, err))

print("\n" + ("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S): {falhas}"))
sys.exit(1 if falhas else 0)
