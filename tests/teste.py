"""Testes da skill popup. Não abrem janela: usam zenity/kdialog falsos (tests/bin).

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
        if k not in ("LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE", "POPUP_IDIOMA", "POPUP_BACKEND",
                     "POPUP_FAVORITAS", "POPUP_ESTADO")}
# Nada de tocar a configuração real do usuário; e uma "tela" falsa para rodar em CI.
base["XDG_CONFIG_HOME"] = os.path.join(S, "config")
base["XDG_STATE_HOME"] = os.path.join(S, "state")
if not base.get("WAYLAND_DISPLAY") and not base.get("DISPLAY"):
    base["DISPLAY"] = ":99"
casos = [
    ({}, "en", None, "en", "--idioma en vence o sistema"),
    ({"LANG": "en_US.UTF-8"}, "pt-BR", None, "pt", "--idioma pt-BR → pt"),
    ({"LANG": "pt_BR.UTF-8", "POPUP_IDIOMA": "es"}, "", None, "es", "POPUP_IDIOMA vence LANG"),
    ({"LANG": "pt_BR.UTF-8"}, "", None, "pt", "LANG pt_BR.UTF-8 → pt"),
    ({"LANG": "es_AR.UTF-8"}, "", None, "es", "LANG es_AR → es"),
    ({"LANGUAGE": "es:en", "LANG": "pt_BR.UTF-8"}, "", None, "es", "LANGUAGE vence LANG (igual gettext)"),
    ({"LC_ALL": "C"}, "", None, "en", "locale C → inglês"),
    ({"LANG": "ko_KR.UTF-8"}, "", None, "en", "LANG coreano (sem tradução) → inglês"),
    ({"LANG": "de_DE.UTF-8"}, "", None, "de", "LANG de_DE → de"),
    ({"LANG": "pt_BR.UTF-8"}, "ko", None, "en", "--idioma ko (sem tradução) → inglês, não o sistema"),
    ({"LANG": "pt_BR.UTF-8", "POPUP_IDIOMA": "ar"}, "", None, "en", "POPUP_IDIOMA ar (sem tradução) → inglês"),
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
    if "POPUP_ESTADO" not in (env_extra or {}):
        env["POPUP_ESTADO"] = tempfile.mkdtemp(dir=S)
    if "POPUP_FAVORITAS" not in (env_extra or {}):
        env["POPUP_FAVORITAS"] = f"{S}/fav-copia.txt"
        _sh.copyfile(FIXTURE_FAV, env["POPUP_FAVORITAS"])
    env.update(env_extra or {})
    r = subprocess.run([f"{SK}/popup.py", *args], capture_output=True, text=True, env=env, timeout=30)
    chamadas = [json.loads(l) for l in open(log) if l.strip()]
    return r.returncode, r.stdout.strip(), r.stderr, chamadas

C = ["--chamada", "Ei", "--pergunta", "Qual?", "--timeout", "30"]
O = ["--opcao", "🧩|Opção A|faz A", "--opcao", "🚀|Opção B|faz B"]

print("2. zenity falso")
cod, out, err, ch = roda(["simnao", "--backend", "zenity", "--idioma", "en", *C], ["0|"])
a = ch[0]["argv"]
checa("simnao en: botões Yes/No", "--ok-label=👍 Yes" in a and "--cancel-label=👎 No" in a, a)
checa("simnao en: saída continua 'sim', exit 0", (cod, out) == (0, "sim"), (cod, out))
cod, out, err, ch = roda(["simnao", "--backend", "zenity", *C], ["1|"], {"POPUP_AGENTE": ""})
checa("sem --idioma usa LANG=pt_BR: botão Sim", "--ok-label=👍 Sim" in ch[0]["argv"], ch[0]["argv"])
checa("simnao 'Não': saída 'não', exit 1", (cod, out) == (1, "não"), (cod, out))
cod, out, err, ch = roda(["pergunta", "--backend", "zenity", "--idioma", "es", *C, *O],
                         ["0|✏️  Escribir otra respuesta…", "0|mi respuesta"])
a1, a2 = ch[0]["argv"], ch[1]["argv"]
checa("pergunta es: linha 'Escribir otra respuesta…'", "✏️  Escribir otra respuesta…" in a1, a1)
checa("pergunta es: botões Elegir / Ahora no", "--ok-label=Elegir" in a1 and "--cancel-label=Ahora no" in a1, a1)
checa("pergunta es: 2ª janela Responder/Ahora no", "--ok-label=Responder" in a2 and "--cancel-label=Ahora no" in a2, a2)
checa("pergunta es: resposta escrita volta no stdout", (cod, out) == (0, "mi respuesta"), (cod, out))
cod, out, err, ch = roda(["pergunta", "--backend", "zenity", "--idioma", "pt", *C, *O], ["0|🚀  Opção B — faz B"])
checa("pergunta pt: escolher cartão devolve o título", (cod, out) == (0, "Opção B"), (cod, out))
cod, out, err, ch = roda(["terminal", "--backend", "zenity", "--idioma", "en", *C], ["5|"])
checa("terminal en: botão 'On my way!'", "--ok-label=🏃 On my way!" in ch[0]["argv"], ch[0]["argv"])
checa("timeout do zenity vira exit 5", cod == 5, cod)
cod, out, err, ch = roda(["simnao", "--idioma", "en", *C], ["0|<FALHA_TELA>", "0|"], desktop="GNOME",
                         env_extra={"POPUP_BACKEND": "zenity,kdialog"})
checa("zenity sem tela → passa para kdialog", [c["prog"] for c in ch] == ["zenity", "kdialog"] and cod == 0,
      ([c["prog"] for c in ch], cod, err))

print("3. kdialog falso (desktop KDE)")
cod, out, err, ch = roda(["pergunta", "--idioma", "en", *C, *O], ["0|outra", "0|typed answer"], desktop="KDE")
checa("KDE escolhe kdialog primeiro", ch and ch[0]["prog"] == "kdialog", ch[:1])
a1 = ch[0]["argv"]
checa("menu en tem 'Write another answer…'", "✏️  Write another answer…" in a1, a1)
checa("'outra' abre inputbox e devolve o texto", ch[1]["argv"][2] == "--inputbox" and (cod, out) == (0, "typed answer"),
      (ch[1]["argv"], cod, out))
cod, out, err, ch = roda(["simnao", "--idioma", "es", *C], ["0|"], desktop="KDE")
checa("simnao es: Sí / No", "👍 Sí" in ch[0]["argv"] and "👎 No" in ch[0]["argv"], ch[0]["argv"])
cod, out, err, ch = roda(["pergunta", "--idioma", "pt", *C, *O], ["0|1"], desktop="KDE")
checa("menu tag 1 devolve 'Opção A'", (cod, out) == (0, "Opção A"), (cod, out))

print("4. diagnostico")
for env, esp in (({"LANG": "es_ES.UTF-8"}, "idioma: es (de sistema (es_ES.UTF-8))"),
                 ({"POPUP_IDIOMA": "en"}, "idioma: en (de POPUP_IDIOMA)")):
    r = subprocess.run([f"{SK}/popup.py", "diagnostico"], capture_output=True, text=True, env=dict(base, **env))
    checa(f"diagnostico mostra '{esp}'", esp in r.stdout, r.stdout)

print("5. Favoritas e histórico (zenity falso)")
import tempfile, shutil, time as _t
FAV = f"{S}/fav-teste.txt"
def novo_estado():
    shutil.copyfile(FIXTURE_FAV, FAV)
    return {"POPUP_ESTADO": tempfile.mkdtemp(dir=S), "POPUP_FAVORITAS": FAV}
F1 = "Chefia, me ajuda numa decisão rapidinha?"
F2 = "Ô parceiro, empaquei numa escolha. Me ajuda?"
def sn(chamada, idioma, env, fila=("0|",), **kw):
    return roda(["simnao", "--backend", "zenity", "--idioma", idioma, "--chamada", chamada,
                 "--pergunta", "P?", "--timeout", "30"], list(fila), env, **kw)
e = novo_estado()
cod, out, err, ch = sn(F1, "pt-BR", e); checa("1ª favorita pt-BR abre", cod == 0 and len(ch) == 1, (cod, err))
cod, out, err, ch = sn(F2, "pt-BR", e); checa("2ª favorita seguida → exit 7, sem janela", cod == 7 and not ch, (cod, ch))
checa("motivo explicado no stderr", "favorita" in err and "rode de novo" in err, err)
cod, out, err, ch = sn("Tem um minutinho pra mim?", "pt-BR", e); checa("chamada nova abre", cod == 0, (cod, err))
cod, out, err, ch = sn(F2, "pt-BR", e); checa("favorita depois de chamada nova abre", cod == 0, (cod, err))
cod, out, err, ch = sn(F1, "pt-BR", e); checa("favorita já usada → exit 7", cod == 7 and "já foi usada" in err, (cod, err))
cod, out, err, ch = sn("  tem UM minutinho   pra mim? ", "pt-BR", e)
checa("chamada nova repetida (maiúsculas/espaços) → exit 7", cod == 7, (cod, err))
cod, out, err, ch = sn(F1, "pt", novo_estado()); checa("--idioma pt equivale a pt-BR", cod == 0, (cod, err))
cod, out, err, ch = sn(F1, "pt-PT", novo_estado()); checa("favorita pt-BR em conversa pt-PT → exit 7", cod == 7 and "pt-BR" in err, (cod, err))
cod, out, err, ch = sn(F1, "en", novo_estado()); checa("favorita pt-BR em conversa en → exit 7", cod == 7, (cod, err))
e = novo_estado()
cod, out, err, ch = sn(F1, "pt-BR", e, env_extra=None) if False else (None,)*4
cod, out, err, ch = roda(["simnao", "--idioma", "pt-BR", "--chamada", F1, "--pergunta", "P?"], [], dict(e, WAYLAND_DISPLAY="", DISPLAY=""))
checa("sem tela (exit 6) não entra no histórico", cod == 6, cod)
cod, out, err, ch = sn(F1, "pt-BR", e); checa("…então a mesma chamada abre depois", cod == 0, (cod, err))
est = f"{e['POPUP_ESTADO']}/historico.json"
import json as _j
d = _j.load(open(est)); [i.update(t=i["t"] - 3*3600) for v in d.values() for i in v]; _j.dump(d, open(est, "w"))
cod, out, err, ch = sn(F1, "pt-BR", e); checa("depois de 2 h sem pop-up a tarefa recomeça", cod == 0, (cod, err))

print("6. Comando favorita")
e = novo_estado()
def fv(*args):
    r = subprocess.run([f"{SK}/popup.py", "favorita", *args], capture_output=True, text=True, env=dict(base, **e))
    return r.returncode, r.stdout.strip()
cod, out = fv("add", "--idioma", "ja", "ちょっといいですか？"); checa("add cria a seção [ja]", cod == 0 and "[ja]" in out and "[ja]\nちょっといいですか？" in open(FAV).read(), (cod, out))
cod, out = fv("add", "--idioma", "ja-JP", "ちょっといいですか？"); checa("add repetido (ja-JP = ja) → 'já estava'", "já estava" in out, out)
cod, out = fv("add", "--idioma", "pt-BR", "Mestre, me dá uma luz aqui?")
txt = open(FAV).read()
checa("add pt-BR entra no fim da seção [pt-BR], antes de [ja]", txt.index("Mestre") < txt.index("\n[ja]\n") and txt.index("Ô parceiro") < txt.index("Mestre"), txt)
checa("comentários do arquivo preservados", txt.startswith("# Chamadas favoritas"), txt[:60])
cod, out = fv("list", "--idioma", "ja"); checa("list --idioma ja mostra só [ja]", "[ja]" in out and "[pt-BR]" not in out, out)
cod, out = fv("rm", "--idioma", "pt-BR", "Mestre, me dá uma luz aqui?"); checa("rm tira", cod == 0 and "Mestre" not in open(FAV).read(), (cod, out))
cod, out = fv("rm", "--idioma", "pt-BR", "Mestre, me dá uma luz aqui?"); checa("rm de algo que não está → exit 1", cod == 1, (cod, out))
cod, out = fv("add", "--idioma", "es", "¿Me das una mano con esto?")
cod, out, err, ch = sn("¿Me das una mano con esto?", "es-MX", e); checa("es-MX usa favoritas de [es]", cod == 0, (cod, err))
r = subprocess.run([f"{SK}/popup.py", "favorita", "add", "sem idioma"], capture_output=True, text=True, env=dict(base, **e, LANG="pt_BR.UTF-8"))
checa("add sem --idioma dá erro", r.returncode != 0, r.returncode)

print("7. Arquivo de favoritas novo")
os.remove(FAV)
cod, out = fv("add", "--idioma", "en", "Hey, can you help me?")
txt = open(FAV).read()
checa("arquivo novo nasce do favoritas.exemplo.txt", "[en]\nHey, can you help me?" in txt and "[pt-BR]" in txt, txt[-200:])
d = os.path.join(S, "cfg-vazio")
r = subprocess.run([f"{SK}/popup.py", "favorita", "add", "--idioma", "es", "¿Me ayudas?"], capture_output=True, text=True,
                   env={k: v for k, v in dict(base, XDG_CONFIG_HOME=d).items() if k != "POPUP_FAVORITAS"})
checa("sem POPUP_FAVORITAS grava em XDG_CONFIG_HOME/popup/favoritas.txt", os.path.exists(f"{d}/popup/favoritas.txt"), r.stderr)

print("\n" + ("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S): {falhas}"))
sys.exit(1 if falhas else 0)
