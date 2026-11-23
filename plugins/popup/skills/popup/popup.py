#!/usr/bin/env python3
"""Pop-up de pergunta ao usuário, com a interface escolhida na hora.

Uso:
  popup.py pergunta --chamada TXT --pergunta TXT [--contexto TXT] \
           [--opcao "emoji|título|descrição"]... [--sem-outra] [--timeout S]
  popup.py simnao   --chamada TXT --pergunta TXT [--contexto TXT] [--timeout S]
  popup.py terminal --chamada TXT --pergunta TXT [--timeout S]
  popup.py diagnostico          mostra o ambiente e a interface que seria usada
  popup.py favorita list [--idioma X]
  popup.py favorita add --idioma X "chamada"
  popup.py favorita rm  --idioma X "chamada"

  --idioma CÓDIGO               idioma dos botões (pt-BR, pt-PT, en, es, fr, de, it, ru, zh, ja);
                                use o mesmo em que escreveu a chamada. Sem tradução → inglês.
                                Sem --idioma: POPUP_IDIOMA, depois o idioma do sistema, senão inglês.
  --backend NOME[,NOME...]      força a interface (ou use POPUP_BACKEND)
                                nomes: gtk, zenity, kdialog, osascript, powershell, tkinter

Saída: a resposta em stdout.
Exit: 0 = respondeu, 1 = fechou/"Agora não"/"Não" (simnao), 5 = timeout,
      6 = sem tela ou sem nenhuma interface disponível (pergunte no terminal),
      7 = chamada recusada (repetida, favorita seguida ou favorita de outro idioma):
          escreva outra chamada e rode de novo. O motivo vai para stderr.
"""
import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textos as tx
import favoritas as fav

AQUI = os.path.dirname(os.path.abspath(__file__))
UI_GTK = os.path.join(AQUI, "ui_gtk.py")

OK, NAO, TIMEOUT, SEM_UI, RECUSADA = 0, 1, 5, 6, 7
MARCA_TIMEOUT = "§TIMEOUT§"

LINUX = sys.platform.startswith(("linux", "freebsd", "openbsd", "netbsd"))
MAC = sys.platform == "darwin"
WINDOWS = sys.platform == "win32"


class Indisponivel(Exception):
    """A interface falhou ao abrir; tente a próxima."""


# ---------------------------------------------------------------- utilidades

def aviso(msg):
    print(f"popup: {msg}", file=sys.stderr)


T = tx.textos(tx.PADRAO)  # trocado em main() pelo idioma escolhido


def titulo_janela():
    try:
        br = subprocess.run(["git", "branch", "--show-current"], capture_output=True,
                            text=True, timeout=2).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        br = ""
    pasta = os.path.basename(os.getcwd())
    agente = os.environ.get("POPUP_AGENTE", T["agente"])
    return f"✨ {agente} · {pasta}" + (f" · {br}" if br else "")


def opcoes(a):
    saida = []
    for spec in a.opcao:
        emoji, titulo, desc = [p.strip() for p in (spec.split("|") + ["", ""])[:3]]
        if not titulo:
            emoji, titulo = "👉", emoji
        saida.append((emoji or "👉", titulo, desc))
    return saida


def rotulo(emoji, titulo, desc):
    return f"{emoji}  {titulo}" + (f" — {desc}" if desc else "")


def texto(a):
    return "\n\n".join(t for t in (a.chamada, a.pergunta, a.contexto) if t)


class Prazo:
    """Conta o tempo total, mesmo quando a pergunta usa duas janelas."""

    def __init__(self, segundos):
        self.fim = time.monotonic() + segundos

    def resta(self):
        return max(0, int(self.fim - time.monotonic()))


def rodar(cmd, timeout, env=None):
    """Roda uma ferramenta de diálogo. Devolve (código, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           timeout=timeout + 3, env=env)
    except subprocess.TimeoutExpired:
        return TIMEOUT, "", ""
    except OSError as e:
        raise Indisponivel(str(e))
    return r.returncode, r.stdout.rstrip("\r\n"), r.stderr


def falhou_tela(cod, err):
    """zenity/kdialog saem com 1 também quando não abrem a tela; separa do "fechou"."""
    e = err.lower()
    return cod == NAO and any(x in e for x in ("open display", "connect to display",
                                               "could not connect", "no such backend"))


def som():
    try:
        if MAC:
            subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif WINDOWS:
            import winsound
            winsound.MessageBeep()
        else:
            subprocess.Popen(["canberra-gtk-play", "-i", "message-new-instant"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, ImportError):
        pass


# ---------------------------------------------------------------- detecção

PROBE_GTK = ('import gi; gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1"); '
             'from gi.repository import Adw, Gtk')
_python_gtk = []


def python_gtk():
    """Acha um Python que importe GTK4 + libadwaita (o do sistema costuma ter)."""
    if not _python_gtk:
        achado = None
        for py in dict.fromkeys([sys.executable, "/usr/bin/python3"]):
            if py and os.path.exists(py):
                try:
                    r = subprocess.run([py, "-c", PROBE_GTK], capture_output=True, timeout=10)
                except (OSError, subprocess.SubprocessError):
                    continue
                if r.returncode == 0:
                    achado = py
                    break
        _python_gtk.append(achado)
    return _python_gtk[0]


def tem_tkinter():
    try:
        import tkinter  # noqa: F401
        return True
    except ImportError:
        return False


def tem_tela():
    if LINUX:
        return bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))
    return True


DISPONIVEL = {
    "gtk": lambda: LINUX and python_gtk() is not None,
    "zenity": lambda: LINUX and shutil.which("zenity") is not None,
    "kdialog": lambda: LINUX and shutil.which("kdialog") is not None,
    "osascript": lambda: MAC and shutil.which("osascript") is not None,
    "powershell": lambda: WINDOWS and (shutil.which("powershell") or shutil.which("pwsh")) is not None,
    "tkinter": tem_tkinter,
}


def desktop():
    return os.environ.get("XDG_CURRENT_DESKTOP", "")


def ordem_padrao():
    if MAC:
        return ["osascript", "tkinter"]
    if WINDOWS:
        return ["tkinter", "powershell"]
    d = desktop().lower()
    if any(x in d for x in ("kde", "lxqt")):
        return ["kdialog", "gtk", "zenity", "tkinter"]
    return ["gtk", "zenity", "kdialog", "tkinter"]


def ordem(forcado):
    if forcado:
        nomes = [n.strip().lower() for n in forcado.split(",") if n.strip()]
        desconhecidos = [n for n in nomes if n not in DISPONIVEL]
        if desconhecidos:
            aviso(f"interface desconhecida: {', '.join(desconhecidos)}")
        return [n for n in nomes if n in DISPONIVEL]
    return ordem_padrao()


def diagnostico(forcado, idioma, origem):
    print(f"sistema: {sys.platform}")
    print(f"idioma: {idioma} (de {origem})")
    if LINUX:
        print(f"sessão: {os.environ.get('XDG_SESSION_TYPE', '?')} · desktop: {desktop() or '?'}")
        print(f"tela: WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', '')} "
              f"DISPLAY={os.environ.get('DISPLAY', '')}")
    lista = ordem(forcado)
    print(f"ordem{' (forçada)' if forcado else ''}: {', '.join(lista)}")
    escolhido = None
    for nome in lista:
        ok = DISPONIVEL[nome]()
        extra = f" ({python_gtk()})" if nome == "gtk" and ok else ""
        print(f"  {nome:<11}{'✓' if ok else '✗'}{extra}")
        if ok and escolhido is None:
            escolhido = nome
    if not tem_tela():
        print("escolhido: nenhum — sem tela (exit 6)")
    else:
        print(f"escolhido: {escolhido or 'nenhum (exit 6)'}")


# ---------------------------------------------------------------- interfaces

def ui_gtk(a):
    cmd = [python_gtk(), UI_GTK, a.modo, "--chamada", a.chamada, "--pergunta", a.pergunta,
           "--contexto", a.contexto, "--timeout", str(a.timeout), "--idioma", a.idioma_fav]
    for o in a.opcao:
        cmd += ["--opcao", o]
    if a.sem_outra:
        cmd.append("--sem-outra")
    cod, out, err = rodar(cmd, a.timeout + 10)
    if cod not in (OK, NAO, TIMEOUT):
        raise Indisponivel(f"saiu com {cod}: {err.strip().splitlines()[-1:] or ''}")
    return out or None, cod


def ui_zenity(a):
    prazo = Prazo(a.timeout)
    som()

    def zenity(*args):
        cmd = ["zenity", f"--title={titulo_janela()}", f"--timeout={max(1, prazo.resta())}",
               "--width=580", *args]
        cod, out, err = rodar(cmd, prazo.resta())
        if cod not in (OK, NAO, TIMEOUT) or falhou_tela(cod, err):
            raise Indisponivel(f"zenity saiu com {cod}: {err.strip()}")
        return cod, out

    t = html.escape(texto(a), quote=False)
    if a.modo == "simnao":
        cod, _ = zenity("--question", f"--text={t}", f"--ok-label=👍 {T['sim']}",
                        f"--cancel-label=👎 {T['nao']}")
        return {OK: "sim", NAO: "não"}.get(cod), cod
    if a.modo == "terminal":
        cod, _ = zenity("--info", f"--text={t}", f"--ok-label=🏃 {T['ja_vou']}")
        return ("ok" if cod == OK else None), cod

    ops = opcoes(a)
    if ops:
        mapa = {rotulo(*o): o[1] for o in ops}
        linhas = list(mapa) + ([] if a.sem_outra else [T["outra"]])
        cod, out = zenity("--list", f"--ok-label={T['escolher']}", f"--cancel-label={T['agora_nao']}", f"--text={t}", "--hide-header", "--column=Opção",
                          f"--height={min(560, 200 + 44 * len(linhas))}", *linhas)
        if cod != OK:
            return None, cod
        if out in mapa:
            return mapa[out], OK
        if out != T["outra"]:
            return None, NAO
    if prazo.resta() <= 0:
        return None, TIMEOUT
    cod, out = zenity("--entry", f"--text={t}", f"--ok-label={T['responder']}",
                      f"--cancel-label={T['agora_nao']}")
    return (out.strip() or None), (cod if out.strip() or cod != OK else NAO)


def ui_kdialog(a):
    prazo = Prazo(a.timeout)
    som()

    def kdialog(*args):
        cmd = ["kdialog", "--title", titulo_janela(), *args]
        cod, out, err = rodar(cmd, max(1, prazo.resta()))
        if cod not in (OK, NAO, TIMEOUT) or falhou_tela(cod, err):
            raise Indisponivel(f"kdialog saiu com {cod}: {err.strip()}")
        return cod, out

    t = texto(a)
    if a.modo == "simnao":
        cod, _ = kdialog("--yes-label", f"👍 {T['sim']}", "--no-label", f"👎 {T['nao']}", "--yesno", t)
        return {OK: "sim", NAO: "não"}.get(cod), cod
    if a.modo == "terminal":
        cod, _ = kdialog("--ok-label", f"🏃 {T['ja_vou']}", "--msgbox", t)
        return ("ok" if cod == OK else None), cod

    ops = opcoes(a)
    if ops:
        args = []
        for i, o in enumerate(ops, 1):
            args += [str(i), rotulo(*o)]
        if not a.sem_outra:
            args += ["outra", T["outra"]]
        cod, out = kdialog("--menu", t, *args)
        if cod != OK:
            return None, cod
        if out.isdigit() and 1 <= int(out) <= len(ops):
            return ops[int(out) - 1][1], OK
        if out != "outra":
            return None, NAO
    if prazo.resta() <= 0:
        return None, TIMEOUT
    cod, out = kdialog("--inputbox", t, "")
    return (out.strip() or None), (cod if out.strip() or cod != OK else NAO)


AS_LISTA = '''on run argv
  set r to choose from list (items 5 thru -1 of argv) with title (item 2 of argv) ¬
    with prompt (item 1 of argv) OK button name (item 3 of argv) cancel button name (item 4 of argv)
  if r is false then error number -128
  return item 1 of r
end run'''

AS_DIALOGO = '''on run argv
  set t to item 1 of argv
  set ttl to item 2 of argv
  set n to (item 3 of argv) as integer
  set modo to item 4 of argv
  set b1 to item 5 of argv
  set b2 to item 6 of argv
  if modo is "texto" then
    set r to display dialog t with title ttl default answer "" buttons {b1, b2} ¬
      default button b2 cancel button b1 giving up after n
    if gave up of r then return "§TIMEOUT§"
    return text returned of r
  else if modo is "simnao" then
    set r to display dialog t with title ttl buttons {b1, b2} default button b2 ¬
      cancel button b1 giving up after n
  else
    set r to display dialog t with title ttl buttons {b1} default button 1 giving up after n
  end if
  if gave up of r then return "§TIMEOUT§"
  return button returned of r
end run'''


def ui_osascript(a):
    prazo = Prazo(a.timeout)
    som()

    def osa(script, *args):
        cod, out, err = rodar(["osascript", "-e", script, "--", *args], max(1, prazo.resta()))
        if cod == TIMEOUT or out == MARCA_TIMEOUT:
            return TIMEOUT, ""
        if cod != OK:
            if "-128" in err:
                return NAO, ""
            raise Indisponivel(f"osascript saiu com {cod}: {err.strip()}")
        return OK, out

    t, ttl = texto(a), titulo_janela()
    if a.modo == "simnao":
        cod, _ = osa(AS_DIALOGO, t, ttl, str(prazo.resta()), "simnao", T["nao"], T["sim"])
        return {OK: "sim", NAO: "não"}.get(cod), cod
    if a.modo == "terminal":
        cod, _ = osa(AS_DIALOGO, t, ttl, str(prazo.resta()), "terminal", T["ja_vou"], "")
        return ("ok" if cod == OK else None), cod

    ops = opcoes(a)
    if ops:
        mapa = {rotulo(*o): o[1] for o in ops}
        linhas = list(mapa) + ([] if a.sem_outra else [T["outra"]])
        cod, out = osa(AS_LISTA, t, ttl, T["escolher"], T["agora_nao"], *linhas)
        if cod != OK:
            return None, cod
        if out in mapa:
            return mapa[out], OK
        if out != T["outra"]:
            return None, NAO
    if prazo.resta() <= 0:
        return None, TIMEOUT
    cod, out = osa(AS_DIALOGO, t, ttl, str(prazo.resta()), "texto", T["agora_nao"], T["responder"])
    return (out.strip() or None), (cod if out.strip() or cod != OK else NAO)


PS_FORM = r'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$d = $env:POPUP_DADOS | ConvertFrom-Json
$script:resp = $null; $script:cod = 1; $script:rest = [int]$d.timeout
$laranja = [Drawing.Color]::FromArgb(217, 119, 87)

$f = New-Object Windows.Forms.Form
$f.Text = $d.titulo; $f.TopMost = $true; $f.StartPosition = 'CenterScreen'
$f.AutoSize = $true; $f.AutoSizeMode = 'GrowAndShrink'; $f.KeyPreview = $true
$f.FormBorderStyle = 'FixedDialog'; $f.MaximizeBox = $false; $f.MinimizeBox = $false
$p = New-Object Windows.Forms.FlowLayoutPanel
$p.FlowDirection = 'TopDown'; $p.WrapContents = $false; $p.AutoSize = $true
$p.Padding = New-Object Windows.Forms.Padding(18)
$f.Controls.Add($p)

function Rotulo($t, $tam, $negrito, $cor) {
  $l = New-Object Windows.Forms.Label
  $l.Text = $t; $l.AutoSize = $true; $l.MaximumSize = New-Object Drawing.Size(540, 0)
  $estilo = if ($negrito) { [Drawing.FontStyle]::Bold } else { [Drawing.FontStyle]::Regular }
  $l.Font = New-Object Drawing.Font('Segoe UI', $tam, $estilo)
  if ($cor) { $l.ForeColor = $cor }
  $l.Margin = New-Object Windows.Forms.Padding(0, 0, 0, 8)
  $p.Controls.Add($l); return $l
}
function Botao($pai, $t, $valor, $codigo, $largo) {
  $b = New-Object Windows.Forms.Button
  $b.Text = $t; $b.Tag = @($valor, $codigo); $b.AutoSize = $true
  $b.Font = New-Object Drawing.Font('Segoe UI', 10)
  if ($largo) { $b.MinimumSize = New-Object Drawing.Size(540, 36); $b.TextAlign = 'MiddleLeft' }
  $b.add_Click({ param($s, $e) $script:resp = $s.Tag[0]; $script:cod = $s.Tag[1]; $s.FindForm().Close() })
  $pai.Controls.Add($b); return $b
}

[void](Rotulo $d.chamada 14 $true $laranja)
[void](Rotulo $d.pergunta 11 $false $null)
if ($d.contexto) { [void](Rotulo $d.contexto 9 $false ([Drawing.Color]::Gray)) }

$ops = @($d.opcoes)
$i = 0
foreach ($o in $ops) { $i++; [void](Botao $p ("$i.  " + $o.rotulo) $o.valor 0 $true) }

$script:tb = $null
if ($d.modo -eq 'pergunta' -and -not $d.sem_outra) {
  $linha = New-Object Windows.Forms.FlowLayoutPanel; $linha.AutoSize = $true; $linha.WrapContents = $false
  $script:tb = New-Object Windows.Forms.TextBox; $script:tb.Width = 430
  $script:tb.Font = New-Object Drawing.Font('Segoe UI', 10)
  $env_ = New-Object Windows.Forms.Button; $env_.Text = $d.t.responder; $env_.AutoSize = $true
  $env_.add_Click({ if ($script:tb.Text.Trim()) { $script:resp = $script:tb.Text.Trim(); $script:cod = 0; $f.Close() } })
  $linha.Controls.Add($script:tb); $linha.Controls.Add($env_); $p.Controls.Add($linha)
  $f.AcceptButton = $env_
}

$rodape = New-Object Windows.Forms.FlowLayoutPanel; $rodape.AutoSize = $true; $rodape.WrapContents = $false
$cont = New-Object Windows.Forms.Label; $cont.AutoSize = $true; $cont.ForeColor = [Drawing.Color]::Gray
$cont.Margin = New-Object Windows.Forms.Padding(0, 8, 12, 0)
$rodape.Controls.Add($cont)
switch ($d.modo) {
  'simnao'   { [void](Botao $rodape $d.t.nao 'não' 1 $false); $f.AcceptButton = (Botao $rodape $d.t.sim 'sim' 0 $false) }
  'terminal' { $f.AcceptButton = (Botao $rodape $d.t.ja_vou 'ok' 0 $false) }
  default    { [void](Botao $rodape $d.t.agora_nao $null 1 $false) }
}
$p.Controls.Add($rodape)

function Contador { $m = [math]::Floor($script:rest / 60); $s = $script:rest % 60
  $cont.Text = $d.cpre + ('{0}:{1:00}' -f $m, $s) + $d.cpos }
Contador
$timer = New-Object Windows.Forms.Timer; $timer.Interval = 1000
$timer.add_Tick({ $script:rest--; if ($script:rest -le 0) { $script:resp = $null; $script:cod = 5; $f.Close() } else { Contador } })
$timer.Start()

$f.add_KeyDown({ param($s, $e)
  if ($e.KeyCode -eq 'Escape') { $script:resp = $null; $script:cod = 1; $f.Close(); return }
  $n = [int]$e.KeyCode - 48
  if ($n -ge 1 -and $n -le 9 -and $n -le $ops.Count -and -not ($script:tb -and $script:tb.Focused)) {
    $script:resp = $ops[$n - 1].valor; $script:cod = 0; $f.Close() }
})
$f.add_Shown({ $f.Activate() })
[void]$f.ShowDialog()
$timer.Stop()
if ($script:resp) { [Console]::Out.Write($script:resp) }
exit $script:cod
'''


def contador_partes():
    """Divide o texto do contador em antes/depois de m:ss, sem o emoji."""
    pre, pos = T["contador"].split("{m}:{s:02d}")
    return pre.replace("⏳", "").lstrip(), pos


def ui_powershell(a):
    exe = shutil.which("powershell") or shutil.which("pwsh")
    dados = {
        "titulo": titulo_janela(), "modo": a.modo, "chamada": a.chamada,
        "pergunta": a.pergunta, "contexto": a.contexto, "timeout": a.timeout,
        "sem_outra": a.sem_outra, "t": T,
        "cpre": contador_partes()[0], "cpos": contador_partes()[1],
        "opcoes": [{"rotulo": rotulo(*o), "valor": o[1]} for o in opcoes(a)],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8-sig") as fh:
        fh.write(PS_FORM)
        caminho = fh.name
    try:
        som()
        env = dict(os.environ, POPUP_DADOS=json.dumps(dados, ensure_ascii=False))
        cod, out, err = rodar([exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-STA",
                               "-File", caminho], a.timeout + 10, env=env)
    finally:
        os.unlink(caminho)
    if cod not in (OK, NAO, TIMEOUT):
        raise Indisponivel(f"powershell saiu com {cod}: {err.strip()}")
    return out or None, cod


def sem_emoji(s):
    """Tk no Linux pode travar com emoji colorido (X BadLength); tira os emoji."""
    if not LINUX:
        return s
    fora = {0xFE0F, 0x200D}
    limpo = "".join(c for c in s if ord(c) <= 0xFFFF and ord(c) not in fora
                    and not 0x2600 <= ord(c) <= 0x27BF)
    return " ".join(limpo.split()) if limpo != s else s


def ui_tkinter(a):
    try:
        import tkinter as tk
        import tkinter.font as tkfont
    except ImportError as e:
        raise Indisponivel(str(e))
    try:
        root = tk.Tk()
    except tk.TclError as e:
        raise Indisponivel(str(e))

    estado = {"r": None, "c": NAO, "rest": a.timeout}

    def fim(r, c):
        estado.update(r=r, c=c)
        root.destroy()

    base = tkfont.nametofont("TkDefaultFont")
    f_chamada = base.copy(); f_chamada.configure(size=15, weight="bold")
    f_pergunta = base.copy(); f_pergunta.configure(size=12)
    f_menor = base.copy(); f_menor.configure(size=9)

    root.title(sem_emoji(titulo_janela()))
    root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", lambda: fim(None, NAO))
    root.bind("<Escape>", lambda _e: fim(None, NAO))

    quadro = tk.Frame(root, padx=24, pady=18)
    quadro.pack(fill="both", expand=True)

    def rot(txt, fonte, cor=None):
        kw = {"fg": cor} if cor else {}
        tk.Label(quadro, text=sem_emoji(txt), font=fonte, wraplength=540, justify="left",
                 anchor="w", **kw).pack(anchor="w", fill="x", pady=(0, 8))

    rot(a.chamada, f_chamada, "#D97757")
    rot(a.pergunta, f_pergunta)
    if a.contexto:
        rot(a.contexto, f_menor, "gray50")

    ops = opcoes(a) if a.modo == "pergunta" else []
    for i, o in enumerate(ops, 1):
        tk.Button(quadro, text=sem_emoji(f"{i}.  {rotulo(*o)}"), anchor="w", justify="left",
                  wraplength=520, padx=10, pady=6,
                  command=lambda t=o[1]: fim(t, OK)).pack(fill="x", pady=2)

    entrada = None
    if a.modo == "pergunta" and not a.sem_outra:
        linha = tk.Frame(quadro)
        linha.pack(fill="x", pady=(8, 0))
        tk.Label(linha, text=T["ou_escreva"]).pack(side="left")
        entrada = tk.Entry(linha)
        entrada.pack(side="left", fill="x", expand=True, padx=6)

        def enviar(_e=None):
            t = entrada.get().strip()
            if t:
                fim(t, OK)
        entrada.bind("<Return>", enviar)
        tk.Button(linha, text=T["responder"], command=enviar).pack(side="left")

    rodape = tk.Frame(quadro)
    rodape.pack(fill="x", pady=(12, 0))
    contador = tk.Label(rodape, font=f_menor, fg="gray50")
    contador.pack(side="left")
    if a.modo == "simnao":
        sim = tk.Button(rodape, text=T["sim"], default="active", command=lambda: fim("sim", OK))
        sim.pack(side="right")
        tk.Button(rodape, text=T["nao"], command=lambda: fim("não", NAO)).pack(side="right", padx=6)
        root.bind("<Return>", lambda _e: fim("sim", OK))
    elif a.modo == "terminal":
        tk.Button(rodape, text=T["ja_vou"], default="active",
                  command=lambda: fim("ok", OK)).pack(side="right")
        root.bind("<Return>", lambda _e: fim("ok", OK))
    else:
        tk.Button(rodape, text=T["agora_nao"], command=lambda: fim(None, NAO)).pack(side="right")

    def tecla(e):
        if ops and e.char.isdigit() and root.focus_get() is not entrada:
            n = int(e.char)
            if 1 <= n <= len(ops):
                fim(ops[n - 1][1], OK)
    root.bind("<Key>", tecla)

    def tick():
        if estado["rest"] <= 0:
            fim(None, TIMEOUT)
            return
        m, s = divmod(estado["rest"], 60)
        pre, pos = contador_partes()
        contador.configure(text=f"{pre}{m}:{s:02d}{pos}")
        estado["rest"] -= 1
        root.after(1000, tick)

    tick()
    som()
    root.attributes("-topmost", True)
    root.after(400, lambda: root.attributes("-topmost", False))
    root.focus_force()
    root.mainloop()
    return estado["r"], estado["c"]


UIS = {"gtk": ui_gtk, "zenity": ui_zenity, "kdialog": ui_kdialog,
       "osascript": ui_osascript, "powershell": ui_powershell, "tkinter": ui_tkinter}


# ---------------------------------------------------------------- principal

def cmd_favorita(p, a):
    acao = a.extra[0] if a.extra else "list"
    texto = " ".join(a.extra[1:]).strip()
    if acao == "list":
        dados = fav.ler()
        alvo = fav.secoes_validas(a.idioma_fav) if a.idioma_bruto else None
        print(f"# {fav.caminho_favoritas()}")
        for s, lista in dados.items():
            if alvo and s not in alvo:
                continue
            print(f"[{s}]")
            for c in lista:
                print(f"  {c}")
        return
    if acao not in ("add", "rm"):
        p.error("use: favorita list | add --idioma X \"chamada\" | rm --idioma X \"chamada\"")
    if not a.idioma_bruto or not texto:
        p.error(f"favorita {acao} precisa de --idioma e do texto da chamada")
    s = fav.secao_para_gravar(a.idioma_bruto)
    if acao == "add":
        ok = fav.adicionar(a.idioma_bruto, texto)
        print(f"{'adicionada' if ok else 'já estava'} em [{s}]")
    else:
        ok = fav.remover(a.idioma_bruto, texto)
        print(f"{'removida de' if ok else 'não estava em'} [{s}]")
        if not ok:
            sys.exit(1)


def main():
    p = argparse.ArgumentParser(description="Pop-up de pergunta ao usuário.")
    p.add_argument("modo", choices=["pergunta", "simnao", "terminal", "diagnostico", "favorita"])
    p.add_argument("extra", nargs="*", help="favorita: list | add TEXTO | rm TEXTO")
    p.add_argument("--chamada")
    p.add_argument("--pergunta")
    p.add_argument("--contexto", default="")
    p.add_argument("--opcao", action="append", default=[])
    p.add_argument("--sem-outra", action="store_true")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--idioma", default="")
    p.add_argument("--backend", default=os.environ.get("POPUP_BACKEND", ""))
    a = p.parse_intermixed_args()  # aceita "favorita add --idioma ja TEXTO"

    global T
    a.idioma_bruto = a.idioma.strip()
    if a.modo == "favorita":
        a.idioma_fav = a.idioma_bruto
        cmd_favorita(p, a)
        return
    if a.extra:
        p.error(f"argumentos inesperados: {' '.join(a.extra)}")
    if a.idioma and not tx.normalizar(a.idioma):
        aviso(f"idioma '{a.idioma}' sem tradução nos botões; usando inglês")
    a.idioma, origem = tx.resolver(a.idioma)
    a.idioma_fav = a.idioma_bruto or a.idioma  # seção de favoritas; 'ko' fica 'ko', não 'en'
    T = tx.textos(a.idioma)

    if a.modo == "diagnostico":
        diagnostico(a.backend, a.idioma, origem)
        return
    if not a.chamada or not a.pergunta:
        p.error("--chamada e --pergunta são obrigatórios")
    if a.modo == "pergunta" and not a.opcao:
        a.sem_outra = False

    motivo = fav.checar(a.chamada, a.idioma_fav)
    if motivo:
        aviso(f"chamada recusada: {motivo}. Escreva outra chamada e rode de novo.")
        sys.exit(RECUSADA)

    if not tem_tela():
        aviso("sem tela (WAYLAND_DISPLAY e DISPLAY vazios); pergunte no terminal")
        sys.exit(SEM_UI)

    for nome in ordem(a.backend):
        if not DISPONIVEL[nome]():
            continue
        try:
            resposta, codigo = UIS[nome](a)
        except Indisponivel as e:
            aviso(f"{nome} falhou ({e}); tentando a próxima interface")
            continue
        if resposta:
            print(resposta)
        try:
            fav.registrar(a.chamada)
        except OSError as e:
            aviso(f"não consegui gravar o histórico ({e})")
        sys.exit(codigo)

    aviso("nenhuma interface gráfica disponível; pergunte no terminal")
    sys.exit(SEM_UI)


if __name__ == "__main__":
    main()
