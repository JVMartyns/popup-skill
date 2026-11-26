"""Notificações do sistema para o modo notification.

Não abre janela e não espera resposta. Linux: notify-send; macOS: osascript;
Windows/WSL: NotifyIcon (balloon tip) pelo PowerShell.
"""
import base64
import os
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
MASCOTE = os.path.join(AQUI, "assets", "mascote.svg")


def _popup():
    import popup  # import tardio: popup.py importa este módulo
    return popup


def backend():
    """Nome do notificador que seria usado, ou None."""
    p = _popup()
    if p.MAC:
        return "osascript" if shutil.which("osascript") else None
    if p.WINDOWS:
        return "powershell" if p.exe_powershell() else None
    if p.WSL:
        return "powershell" if p.exe_powershell() else None
    return "notify-send" if shutil.which("notify-send") else None


def disponivel():
    return backend() is not None


def descricao():
    return backend() or "none"


def _aspas(s):
    """String literal do AppleScript."""
    return '"' + " ".join(str(s).split()).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _ps(s):
    """String literal do PowerShell (aspas simples)."""
    return "'" + str(s).replace("'", "''") + "'"


def _windows(titulo, corpo, urgente):
    p = _popup()
    exe = p.exe_powershell()
    if not exe:
        return False
    script = (
        "Add-Type -AssemblyName System.Windows.Forms\n"
        "Add-Type -AssemblyName System.Drawing\n"
        "$n = New-Object System.Windows.Forms.NotifyIcon\n"
        "$n.Icon = [System.Drawing.SystemIcons]::Information\n"
        f"$n.BalloonTipTitle = {_ps(titulo)}\n"
        f"$n.BalloonTipText = {_ps(corpo)}\n"
        "$n.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::"
        + ("Warning" if urgente else "Info") + "\n"
        "$n.Visible = $true\n"
        "$n.ShowBalloonTip(5000)\n"
        "Start-Sleep -Seconds 6\n"
        "$n.Dispose()\n"
    )
    codificado = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    cmd = [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
           "-WindowStyle", "Hidden", "-STA", "-EncodedCommand", codificado]
    cwd = "/mnt/c" if p.WSL and os.path.isdir("/mnt/c") else None
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=20, cwd=cwd)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def enviar(a, urgente=False):
    """Manda a notificação. Devolve True/False; não abre janela."""
    p = _popup()
    titulo = p.titulo_janela()
    corpo = p.texto(a)
    b = backend()
    if b == "notify-send":
        cmd = ["notify-send", "--app-name=Popup", f"--icon={MASCOTE}",
               f"--urgency={'critical' if urgente else 'normal'}", titulo, corpo]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return False
        return r.returncode == 0
    if b == "osascript":
        script = f"display notification {_aspas(corpo)} with title {_aspas(titulo)}"
        try:
            r = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return False
        return r.returncode == 0
    if b == "powershell":
        return _windows(titulo, corpo, urgente)
    return False
