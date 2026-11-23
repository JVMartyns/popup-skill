#!/usr/bin/env python3
"""Ask the user through a desktop pop-up, with the interface chosen at run time.

Usage:
  popup.py ask      --greeting TXT --question TXT [--context TXT] \
                    [--option "emoji|title|description"]... [--no-other] [--timeout S]
  popup.py yesno    --greeting TXT --question TXT [--context TXT] [--timeout S]
  popup.py terminal --greeting TXT --question TXT [--timeout S]
  popup.py doctor                         show the environment and the interface that would be used
  popup.py favorite list [--lang X]
  popup.py favorite add --lang X "greeting"
  popup.py favorite rm  --lang X "greeting"

  --lang CODE        language of the window texts (pt-BR, pt-PT, en, es, fr, de, it, ru, zh, ja);
                     use the one you wrote the greeting in. No translation → English.
                     Without --lang: POPUP_LANG, then the system language, then English.
  --backend NAME[,NAME...]  force the interface (or POPUP_BACKEND):
                     gtk, zenity, kdialog, osascript, powershell, tkinter

Output: the answer on stdout (yesno: "yes"/"no"; terminal: "ok").
Exit: 0 = answered, 1 = closed / "Not now" / "No" (yesno), 5 = timeout,
      6 = no screen or no interface available (ask in the terminal),
      7 = greeting refused (repeated, favorite after favorite, or favorite of another
          language): write another greeting and run again. The reason goes to stderr.

Portuguese names from version 0.1 still work as aliases: pergunta, simnao, diagnostico,
favorita, --chamada, --pergunta, --contexto, --opcao, --sem-outra, --idioma.
"""
import argparse
import base64
import html
import json
import os
import shutil
import subprocess
import sys
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


def _detecta_wsl():
    if not sys.platform.startswith("linux"):
        return False
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    try:
        with open("/proc/sys/kernel/osrelease") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


WSL = _detecta_wsl()  # Linux dentro do Windows: dá para abrir janela nativa do Windows


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
    agente = tx.env("POPUP_AGENT", "POPUP_AGENTE") or T["agente"]
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


def rodar(cmd, timeout, env=None, cwd=None):
    """Roda uma ferramenta de diálogo. Devolve (código, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout + 3, env=env, cwd=cwd)
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


def tela_x():
    return bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))


def tem_tkinter():
    try:
        import tkinter  # noqa: F401
        return True
    except ImportError:
        return False


WSL_POWERSHELL = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"


def exe_powershell():
    """powershell.exe do Windows (nativo ou pelo WSL), ou pwsh."""
    if WINDOWS:
        return shutil.which("powershell") or shutil.which("pwsh")
    if WSL:
        return shutil.which("powershell.exe") or (WSL_POWERSHELL if os.path.exists(WSL_POWERSHELL) else None)
    return None


def tem_tela():
    if LINUX:
        if WSL and exe_powershell():
            return True  # a janela abre no Windows, mesmo sem WSLg
        return bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))
    return True


DISPONIVEL = {
    "gtk": lambda: LINUX and tela_x() and python_gtk() is not None,
    "zenity": lambda: LINUX and tela_x() and shutil.which("zenity") is not None,
    "kdialog": lambda: LINUX and tela_x() and shutil.which("kdialog") is not None,
    "osascript": lambda: MAC and shutil.which("osascript") is not None,
    "powershell": lambda: exe_powershell() is not None,
    "tkinter": lambda: (not LINUX or tela_x()) and tem_tkinter(),
}


def desktop():
    return os.environ.get("XDG_CURRENT_DESKTOP", "")


def ordem_padrao():
    if MAC:
        return ["osascript", "tkinter"]
    if WINDOWS:
        return ["tkinter", "powershell"]
    if WSL:
        # janela nativa do Windows primeiro: não depende do WSLg nem de pacotes Linux
        return ["powershell", "gtk", "zenity", "kdialog", "tkinter"]
    d = desktop().lower()
    if any(x in d for x in ("kde", "lxqt")):
        return ["kdialog", "gtk", "zenity", "tkinter"]
    return ["gtk", "zenity", "kdialog", "tkinter"]


def ordem(forcado):
    if forcado:
        nomes = [n.strip().lower() for n in forcado.split(",") if n.strip()]
        desconhecidos = [n for n in nomes if n not in DISPONIVEL]
        if desconhecidos:
            aviso(f"unknown interface: {', '.join(desconhecidos)}")
        return [n for n in nomes if n in DISPONIVEL]
    return ordem_padrao()


def diagnostico(forcado, idioma, origem):
    print(f"system: {sys.platform}")
    print(f"language: {idioma} (from {origem})")
    if WSL:
        print(f"wsl: yes · powershell.exe: {exe_powershell() or 'not found'}")
    if LINUX:
        print(f"session: {os.environ.get('XDG_SESSION_TYPE', '?')} · desktop: {desktop() or '?'}")
        print(f"screen: WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', '')} "
              f"DISPLAY={os.environ.get('DISPLAY', '')}")
    lista = ordem(forcado)
    print(f"order{' (forced)' if forcado else ''}: {', '.join(lista)}")
    escolhido = None
    for nome in lista:
        ok = DISPONIVEL[nome]()
        extra = f" ({python_gtk()})" if nome == "gtk" and ok else ""
        print(f"  {nome:<11}{'✓' if ok else '✗'}{extra}")
        if ok and escolhido is None:
            escolhido = nome
    if not tem_tela():
        print("chosen: none — no screen (exit 6)")
    else:
        print(f"chosen: {escolhido or 'none (exit 6)'}")


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
        raise Indisponivel(f"exited with {cod}: {err.strip().splitlines()[-1:] or ''}")
    return out or None, cod


def ui_zenity(a):
    prazo = Prazo(a.timeout)
    som()

    def zenity(*args):
        cmd = ["zenity", f"--title={titulo_janela()}", f"--timeout={max(1, prazo.resta())}",
               "--width=580", *args]
        cod, out, err = rodar(cmd, prazo.resta())
        if cod not in (OK, NAO, TIMEOUT) or falhou_tela(cod, err):
            raise Indisponivel(f"zenity exited with {cod}: {err.strip()}")
        return cod, out

    t = html.escape(texto(a), quote=False)
    if a.modo == "simnao":
        cod, _ = zenity("--question", f"--text={t}", f"--ok-label=👍 {T['sim']}",
                        f"--cancel-label=👎 {T['nao']}")
        return {OK: "yes", NAO: "no"}.get(cod), cod
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
            raise Indisponivel(f"kdialog exited with {cod}: {err.strip()}")
        return cod, out

    t = texto(a)
    if a.modo == "simnao":
        cod, _ = kdialog("--yes-label", f"👍 {T['sim']}", "--no-label", f"👎 {T['nao']}", "--yesno", t)
        return {OK: "yes", NAO: "no"}.get(cod), cod
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
            raise Indisponivel(f"osascript exited with {cod}: {err.strip()}")
        return OK, out

    t, ttl = texto(a), titulo_janela()
    if a.modo == "simnao":
        cod, _ = osa(AS_DIALOGO, t, ttl, str(prazo.resta()), "simnao", T["nao"], T["sim"])
        return {OK: "yes", NAO: "no"}.get(cod), cod
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
# Erro interno sai com 3 (não com 1, que é "usuário fechou"): popup.py tenta a próxima interface.
trap { [Console]::Error.WriteLine("popup.ps1: " + $_.ToString()); exit 3 }
$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$d = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__DADOS_B64__')) | ConvertFrom-Json
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
  'simnao'   { [void](Botao $rodape $d.t.nao 'no' 1 $false); $f.AcceptButton = (Botao $rodape $d.t.sim 'yes' 0 $false) }
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
$f.add_Shown({ $f.Activate(); [System.Media.SystemSounds]::Asterisk.Play() })
[void]$f.ShowDialog()
$timer.Stop()
if ($script:resp) { [Console]::Out.Write($script:resp) }
exit $script:cod
'''


def contador_partes():
    """Divide o texto do contador em antes/depois de m:ss, sem o emoji."""
    pre, pos = T["contador"].split("{m}:{s:02d}")
    return pre.replace("⏳", "").lstrip(), pos


LIMITE_LINHA_COMANDO = 32000  # o Windows aceita até 32767 caracteres


def comando_powershell(a, exe):
    """Monta o comando: script e dados vão em -EncodedCommand, sem arquivo temporário
    nem variável de ambiente (que não atravessam do WSL para o Windows sem WSLENV)."""
    dados = {
        "titulo": titulo_janela(), "modo": a.modo, "chamada": a.chamada,
        "pergunta": a.pergunta, "contexto": a.contexto, "timeout": a.timeout,
        "sem_outra": a.sem_outra, "t": T,
        "cpre": contador_partes()[0], "cpos": contador_partes()[1],
        "opcoes": [{"rotulo": rotulo(*o), "valor": o[1]} for o in opcoes(a)],
    }
    b64_dados = base64.b64encode(json.dumps(dados, ensure_ascii=False).encode("utf-8")).decode("ascii")
    script = PS_FORM.replace("__DADOS_B64__", b64_dados)
    codificado = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    cmd = [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-STA",
           "-EncodedCommand", codificado]
    if sum(len(c) + 1 for c in cmd) > LIMITE_LINHA_COMANDO:
        raise Indisponivel("question too long for the PowerShell command line")
    return cmd


def ui_powershell(a):
    exe = exe_powershell()
    cmd = comando_powershell(a, exe)
    # No WSL, rodar o .exe numa pasta Linux faz o Windows reclamar de caminho UNC.
    cwd = "/mnt/c" if WSL and os.path.isdir("/mnt/c") else None
    cod, out, err = rodar(cmd, a.timeout + 15, cwd=cwd)
    if cod not in (OK, NAO, TIMEOUT):
        raise Indisponivel(f"powershell exited with {cod}: {err.strip()[-300:]}")
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
        sim = tk.Button(rodape, text=T["sim"], default="active", command=lambda: fim("yes", OK))
        sim.pack(side="right")
        tk.Button(rodape, text=T["nao"], command=lambda: fim("no", NAO)).pack(side="right", padx=6)
        root.bind("<Return>", lambda _e: fim("yes", OK))
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
        p.error('use: favorite list | add --lang X "greeting" | rm --lang X "greeting"')
    if not a.idioma_bruto or not texto:
        p.error(f"favorite {acao} needs --lang and the greeting text")
    s = fav.secao_para_gravar(a.idioma_bruto)
    if acao == "add":
        ok = fav.adicionar(a.idioma_bruto, texto)
        print(f"{'added to' if ok else 'already in'} [{s}]")
    else:
        ok = fav.remover(a.idioma_bruto, texto)
        print(f"{'removed from' if ok else 'not in'} [{s}]")
        if not ok:
            sys.exit(1)


MODOS = {  # nome público → nome interno
    "ask": "pergunta", "yesno": "simnao", "terminal": "terminal",
    "doctor": "diagnostico", "favorite": "favorita",
    # apelidos em português da versão 0.1
    "pergunta": "pergunta", "simnao": "simnao", "diagnostico": "diagnostico", "favorita": "favorita",
}


def main():
    p = argparse.ArgumentParser(prog="popup.py", description="Ask the user through a desktop pop-up.")
    p.add_argument("modo", choices=list(MODOS), metavar="{ask,yesno,terminal,doctor,favorite}")
    p.add_argument("extra", nargs="*", help="favorite: list | add TEXT | rm TEXT")

    def opcao(novo, antigo, dest, **kw):
        if kw.get("action") != "store_true":
            kw.setdefault("metavar", "CODE" if novo == "--lang" else "TEXT")
        p.add_argument(novo, dest=dest, **kw)
        kw.pop("help", None)
        kw["default"] = argparse.SUPPRESS
        p.add_argument(antigo, dest=dest, help=argparse.SUPPRESS, **kw)

    opcao("--greeting", "--chamada", "chamada", help="friendly opening line (agent-written)")
    opcao("--question", "--pergunta", "pergunta", help="the question itself")
    opcao("--context", "--contexto", "contexto", default="", help="optional supporting line")
    opcao("--option", "--opcao", "opcao", action="append", default=[], help='"emoji|title|description"')
    opcao("--no-other", "--sem-outra", "sem_outra", action="store_true", default=False,
          help="ask: no free-text field")
    opcao("--lang", "--idioma", "idioma", default="", help="language code of the conversation")
    p.add_argument("--timeout", type=int, default=300, metavar="S", help="seconds (default 300)")
    p.add_argument("--backend", default=os.environ.get("POPUP_BACKEND", ""), metavar="NAMES",
                   help="force interface(s): gtk,zenity,kdialog,osascript,powershell,tkinter")
    a = p.parse_intermixed_args()  # aceita "favorite add --lang ja TEXTO"
    a.modo = MODOS[a.modo]

    global T
    a.idioma_bruto = a.idioma.strip()
    if a.modo == "favorita":
        a.idioma_fav = a.idioma_bruto
        cmd_favorita(p, a)
        return
    if a.extra:
        p.error(f"unexpected arguments: {' '.join(a.extra)}")
    if a.idioma and not tx.normalizar(a.idioma):
        aviso(f"no window texts for language '{a.idioma}'; using English")
    a.idioma, origem = tx.resolver(a.idioma)
    a.idioma_fav = a.idioma_bruto or a.idioma  # seção de favoritas; 'ko' fica 'ko', não 'en'
    T = tx.textos(a.idioma)

    if a.modo == "diagnostico":
        diagnostico(a.backend, a.idioma, origem)
        return
    if not a.chamada or not a.pergunta:
        p.error("--greeting and --question are required")
    if a.modo == "pergunta" and not a.opcao:
        a.sem_outra = False

    motivo = fav.checar(a.chamada, a.idioma_fav)
    if motivo:
        aviso(f"greeting refused: {motivo}. Write another greeting and run again.")
        sys.exit(RECUSADA)

    if not tem_tela():
        aviso("no screen (WAYLAND_DISPLAY and DISPLAY are empty); ask in the terminal")
        sys.exit(SEM_UI)

    for nome in ordem(a.backend):
        if not DISPONIVEL[nome]():
            continue
        try:
            resposta, codigo = UIS[nome](a)
        except Indisponivel as e:
            aviso(f"{nome} failed ({e}); trying the next interface")
            continue
        if resposta:
            print(resposta)
        try:
            fav.registrar(a.chamada)
        except OSError as e:
            aviso(f"could not save the history ({e})")
        sys.exit(codigo)

    aviso("no graphical interface available; ask in the terminal")
    sys.exit(SEM_UI)


if __name__ == "__main__":
    main()
