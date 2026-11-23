#!/usr/bin/python3
"""Desenha a janela GTK num PNG (para o README). Abre a janela por ~1 s.

Uso: tests/manual/screenshot_gtk.py SAIDA.png <argumentos do ui_gtk.py>
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "skills", "popup"))
import ui_gtk  # noqa: E402
from gi.repository import GLib, Graphene, Gtk  # noqa: E402

SAIDA = sys.argv.pop(1)
orig = ui_gtk.Popup._montar


def montar(self, app):
    orig(self, app)

    def foto():
        w, h = self.win.get_width(), self.win.get_height()
        snap = Gtk.Snapshot()
        Gtk.WidgetPaintable.new(self.win).snapshot(snap, w, h)
        node = snap.to_node()
        tex = self.win.get_renderer().render_texture(node, Graphene.Rect().init(0, 0, w, h))
        tex.save_to_png(SAIDA)
        self.responder(None, 5)
        return False

    GLib.timeout_add(900, foto)


ui_gtk.Popup._montar = montar
ui_gtk.main()
