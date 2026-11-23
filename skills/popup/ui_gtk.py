#!/usr/bin/python3
"""Interface GTK4 + libadwaita do pop-up. Chamada por popup.py; não use direto.

Uso:
  ui_gtk.py pergunta --chamada TXT --pergunta TXT [--contexto TXT] \
           [--opcao "emoji|título|descrição"]... [--sem-outra] [--timeout S]
  ui_gtk.py simnao   --chamada TXT --pergunta TXT [--contexto TXT] [--timeout S]
  ui_gtk.py terminal --chamada TXT --pergunta TXT [--timeout S]

Saída: a resposta em stdout.
Exit: 0 = respondeu, 1 = fechou/"Agora não"/"Não" (simnao), 5 = timeout, 3 = erro.
"""
import argparse
import os
import subprocess
import sys
import traceback

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
import textos as tx  # noqa: E402
import favoritas as fav  # noqa: E402

T = tx.textos(tx.PADRAO)  # trocado em main() pelo --idioma

ERRO = 3  # não abriu; popup.py tenta a próxima interface

AQUI = os.path.dirname(os.path.abspath(__file__))
MASCOTE = os.path.join(AQUI, "assets", "mascote.svg")

CSS = """
.popup-bg {
  background: linear-gradient(180deg, alpha(#D97757, 0.16) 0%, transparent 46%), @window_bg_color;
}
.chamada {
  font-size: 19pt; font-weight: 800; color: #D97757; letter-spacing: -0.2px;
}
.pergunta { font-size: 13pt; }
.contexto { font-size: 10pt; opacity: 0.65; }
.selo {
  background: alpha(#D97757, 0.15); color: #D97757; border-radius: 99px;
  padding: 2px 10px; font-size: 9pt; font-weight: 700;
}
.opcao { border-radius: 14px; padding: 4px 2px; transition: all 150ms ease; }
.opcao:hover { background: alpha(#D97757, 0.12); }
.opcao .emoji { font-size: 22pt; }
.opcao .titulo { font-weight: 700; font-size: 12pt; }
.opcao .desc { opacity: 0.65; font-size: 10pt; }
.tecla {
  font-family: monospace; font-size: 9pt; font-weight: 700; opacity: 0.55;
  border: 1px solid alpha(currentColor, 0.35); border-radius: 6px; padding: 0 6px;
}
.contador { font-size: 9pt; opacity: 0.5; font-variant-numeric: tabular-nums; }
.btn-principal { background: #D97757; color: white; font-weight: 700; }
.btn-principal:hover { background: #C9623F; }
@keyframes balanca { 0% { margin-top: 0px; } 50% { margin-top: -6px; } 100% { margin-top: 0px; } }
.mascote { animation: balanca 1.6s ease-in-out infinite; }
"""


def tocar_som():
    try:
        subprocess.Popen(["canberra-gtk-play", "-i", "message-new-instant"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def titulo_janela():
    try:
        br = subprocess.run(["git", "branch", "--show-current"], capture_output=True,
                            text=True, timeout=2).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        br = ""
    pasta = os.path.basename(os.getcwd())
    agente = tx.env("POPUP_AGENT", "POPUP_AGENTE") or T["agente"]
    return f"✨ {agente} · {pasta}" + (f" · {br}" if br else "")


class Popup(Adw.Application):
    def __init__(self, a):
        super().__init__(application_id=None)
        self.a = a
        self.resposta = None
        self.codigo = 1
        self.restante = a.timeout
        self.connect("activate", self.montar)

    # ---------- saída ----------
    def responder(self, texto, codigo=0):
        self.resposta, self.codigo = texto, codigo
        self.win.close()

    # ---------- montagem ----------
    def montar(self, app):
        try:
            self._montar(app)
        except Exception:
            traceback.print_exc()
            self.codigo = ERRO
            self.quit()

    def _montar(self, _app):
        prov = Gtk.CssProvider()
        prov.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=self, title=titulo_janela())
        self.win.set_default_size(620, -1)
        self.win.set_resizable(False)

        raiz = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        raiz.add_css_class("popup-bg")
        header = Adw.HeaderBar()
        header.add_css_class("flat")
        selo = Gtk.Label(label=self.selo_texto())
        selo.add_css_class("selo")
        header.set_title_widget(selo)
        header.pack_end(self.botao_favorita())
        raiz.append(header)

        corpo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14,
                        margin_start=28, margin_end=28, margin_bottom=22, margin_top=4)
        raiz.append(corpo)

        topo = Gtk.Box(spacing=16)
        if os.path.exists(MASCOTE):
            img = Gtk.Image.new_from_file(MASCOTE)
            img.set_pixel_size(72)
            img.set_valign(Gtk.Align.START)
            img.add_css_class("mascote")
            topo.append(img)
        textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, hexpand=True)
        textos.append(self.rotulo(self.a.chamada, "chamada"))
        textos.append(self.rotulo(self.a.pergunta, "pergunta"))
        if self.a.contexto:
            textos.append(self.rotulo(self.a.contexto, "contexto"))
        topo.append(textos)
        corpo.append(topo)

        getattr(self, f"corpo_{self.a.modo}")(corpo)

        rodape = Gtk.Box(spacing=8, margin_top=4)
        self.lbl_contador = Gtk.Label(hexpand=True, xalign=0)
        self.lbl_contador.add_css_class("contador")
        rodape.append(self.lbl_contador)
        for w in self.botoes_rodape():
            rodape.append(w)
        corpo.append(rodape)

        self.win.set_content(raiz)
        teclas = Gtk.EventControllerKey()
        teclas.connect("key-pressed", self.tecla)
        self.win.add_controller(teclas)

        self.tick()
        GLib.timeout_add_seconds(1, self.tick)
        tocar_som()
        self.win.present()

    def botao_favorita(self):
        """⭐ guarda a chamada atual nas favoritas do idioma; clicar de novo tira."""
        self.codigo_fav = self.a.idioma_fav
        self.btn_fav = Gtk.Button()
        self.btn_fav.add_css_class("flat")
        self.btn_fav.set_focus_on_click(False)
        self.btn_fav.connect("clicked", self.alternar_favorita)
        self.mostrar_favorita(fav.secao_de(self.a.chamada) in fav.secoes_validas(self.codigo_fav))
        return self.btn_fav

    def mostrar_favorita(self, marcada):
        self.btn_fav.set_label("⭐" if marcada else "☆")
        self.btn_fav.set_tooltip_text(T["fav_salva"] if marcada else T["fav_salvar"])
        self.fav_marcada = marcada

    def alternar_favorita(self, *_):
        try:
            if self.fav_marcada:
                fav.remover(self.codigo_fav, self.a.chamada)
            else:
                fav.adicionar(self.codigo_fav, self.a.chamada)
        except (OSError, ValueError) as e:
            print(f"ui_gtk: could not save the favorite ({e})", file=sys.stderr)
            return
        self.mostrar_favorita(not self.fav_marcada)

    def selo_texto(self):
        return T[f"selo_{self.a.modo}"]

    @staticmethod
    def rotulo(txt, classe):
        lb = Gtk.Label(label=txt, wrap=True, xalign=0, max_width_chars=48, selectable=False)
        lb.add_css_class(classe)
        return lb

    # ---------- modos ----------
    def corpo_pergunta(self, corpo):
        lista = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        lista.add_css_class("boxed-list")
        self.opcoes = []
        for i, spec in enumerate(self.a.opcao, 1):
            partes = (spec.split("|") + ["", ""])[:3]
            emoji, titulo, desc = [p.strip() for p in partes]
            if not titulo:
                emoji, titulo = "👉", emoji
            self.opcoes.append(titulo)
            lista.append(self.linha_opcao(i, emoji or "👉", titulo, desc))
        lista.connect("row-activated",
                      lambda _l, row: self.responder(self.opcoes[row.get_index()]))
        corpo.append(lista)
        GLib.idle_add(lambda: lista.get_row_at_index(0) and lista.get_row_at_index(0).grab_focus() and False)

        if not self.a.sem_outra:
            caixa = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
            caixa.add_css_class("boxed-list")
            self.entrada = Adw.EntryRow(title=T["entrada"])
            self.entrada.set_show_apply_button(True)
            self.entrada.connect("entry-activated", self.enviar_texto)
            self.entrada.connect("apply", self.enviar_texto)
            caixa.append(self.entrada)
            corpo.append(caixa)

    def linha_opcao(self, i, emoji, titulo, desc):
        row = Gtk.ListBoxRow(activatable=True)
        row.add_css_class("opcao")
        caixa = Gtk.Box(spacing=14, margin_start=12, margin_end=12, margin_top=8, margin_bottom=8)
        e = Gtk.Label(label=emoji)
        e.add_css_class("emoji")
        caixa.append(e)
        tx = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True,
                     valign=Gtk.Align.CENTER)
        t = Gtk.Label(label=titulo, xalign=0, wrap=True)
        t.add_css_class("titulo")
        tx.append(t)
        if desc:
            d = Gtk.Label(label=desc, xalign=0, wrap=True)
            d.add_css_class("desc")
            tx.append(d)
        caixa.append(tx)
        if i <= 9:
            k = Gtk.Label(label=str(i), valign=Gtk.Align.CENTER)
            k.add_css_class("tecla")
            caixa.append(k)
        row.set_child(caixa)
        return row

    def corpo_simnao(self, corpo):
        pass

    def corpo_terminal(self, corpo):
        pass

    def botoes_rodape(self):
        def botao(rotulo, cb, principal=False):
            b = Gtk.Button(label=rotulo)
            b.add_css_class("pill")
            if principal:
                b.add_css_class("btn-principal")
            b.connect("clicked", lambda *_: cb())
            return b

        if self.a.modo == "simnao":
            sim = botao(f"👍  {T['sim']}", lambda: self.responder("yes", 0), True)
            self.win.set_default_widget(sim)
            return [botao(f"👎  {T['nao']}", lambda: self.responder("no", 1)), sim]
        if self.a.modo == "terminal":
            ok = botao(f"🏃  {T['ja_vou']}", lambda: self.responder("ok", 0), True)
            self.win.set_default_widget(ok)
            return [ok]
        return [botao(T["agora_nao"], lambda: self.responder(None, 1))]

    # ---------- eventos ----------
    def enviar_texto(self, *_):
        txt = self.entrada.get_text().strip()
        if txt:
            self.responder(txt)

    def tecla(self, _ctl, keyval, _code, _state):
        if keyval == Gdk.KEY_Escape:
            self.responder(None, 1)
            return True
        if self.a.modo == "pergunta" and not (
                hasattr(self, "entrada") and self.entrada.has_focus()
                or (hasattr(self, "entrada") and self.entrada.get_text())):
            nome = (Gdk.keyval_name(keyval) or "").removeprefix("KP_")
            n = nome if len(nome) == 1 and nome.isdigit() else ""
            if n and 1 <= int(n) <= len(self.opcoes):
                self.responder(self.opcoes[int(n) - 1])
                return True
        return False

    def tick(self):
        if self.restante <= 0:
            self.responder(None, 5)
            return False
        m, s = divmod(self.restante, 60)
        self.lbl_contador.set_label(T["contador"].format(m=m, s=s))
        self.restante -= 1
        return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("modo", choices=["pergunta", "simnao", "terminal"])
    p.add_argument("--chamada", required=True)
    p.add_argument("--pergunta", required=True)
    p.add_argument("--contexto", default="")
    p.add_argument("--opcao", action="append", default=[])
    p.add_argument("--sem-outra", action="store_true")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--idioma", default="")
    a = p.parse_args()
    global T
    idioma = tx.resolver(a.idioma)[0]
    T = tx.textos(idioma)
    a.idioma_fav = a.idioma.strip() or idioma
    if a.modo == "pergunta" and not a.opcao:
        a.sem_outra = False
    if not Gtk.init_check():
        print("ui_gtk: could not open the screen", file=sys.stderr)
        sys.exit(ERRO)
    app = Popup(a)
    app.run([sys.argv[0]])
    if app.resposta:
        print(app.resposta)
    sys.exit(app.codigo)


if __name__ == "__main__":
    main()
