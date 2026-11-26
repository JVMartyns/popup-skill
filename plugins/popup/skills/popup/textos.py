"""Textos fixos da janela por idioma, e a escolha do idioma.

Ordem: --lang → POPUP_LANG → idioma do sistema → inglês.
Um idioma pedido em --lang ou POPUP_LANG sem tradução vira inglês (não cai no
sistema): o agente já escreveu a chamada nesse idioma, e inglês combina melhor do que
o idioma do sistema. (--idioma e POPUP_IDIOMA são apelidos antigos.)
A chamada, a pergunta e as opções não passam por aqui: o agente as escreve.

"""
import locale
import os
import subprocess
import sys

PADRAO = "en"

def env(*nomes):
    """Primeira variável de ambiente definida (nome novo primeiro, apelidos depois)."""
    for n in nomes:
        v = os.environ.get(n)
        if v:
            return v
    return None

TEXTOS = {
    "pt": {
        "agente": "Agente",
        "sim": "Sim", "nao": "Não", "ja_vou": "Já vou!",
        "agora_nao": "Agora não", "responder": "Responder", "escolher": "Escolher",
        "outra": "✏️  Escrever outra resposta…",
        "ou_escreva": "Ou escreva:",
        "entrada": "✏️  Ou escreva sua resposta e aperte Enter",
        "contador": "⏳ fecha sozinho em {m}:{s:02d} · Esc fecha",
        "selo_pergunta": "PERGUNTA RÁPIDA",
        "selo_simnao": "SIM OU NÃO?",
        "selo_terminal": "TE ESPERO NO TERMINAL",
        "selo_notify": "TAREFA CONCLUÍDA",
        "ok": "OK",
        "fav_salvar": "Guardar esta chamada nas favoritas",
        "fav_salva": "Está nas favoritas (clique para tirar)",
    },
    "en": {
        "agente": "Agent",
        "sim": "Yes", "nao": "No", "ja_vou": "On my way!",
        "agora_nao": "Not now", "responder": "Answer", "escolher": "Choose",
        "outra": "✏️  Write another answer…",
        "ou_escreva": "Or type:",
        "entrada": "✏️  Or type your answer and press Enter",
        "contador": "⏳ closes in {m}:{s:02d} · Esc closes",
        "selo_pergunta": "QUICK QUESTION",
        "selo_simnao": "YES OR NO?",
        "selo_terminal": "SEE YOU IN THE TERMINAL",
        "selo_notify": "TASK COMPLETED",
        "ok": "OK",
        "fav_salvar": "Save this greeting to favorites",
        "fav_salva": "In favorites (click to remove)",
    },
    "es": {
        "agente": "Agente",
        "sim": "Sí", "nao": "No", "ja_vou": "¡Ya voy!",
        "agora_nao": "Ahora no", "responder": "Responder", "escolher": "Elegir",
        "outra": "✏️  Escribir otra respuesta…",
        "ou_escreva": "O escribe:",
        "entrada": "✏️  O escribe tu respuesta y pulsa Enter",
        "contador": "⏳ se cierra en {m}:{s:02d} · Esc cierra",
        "selo_pergunta": "PREGUNTA RÁPIDA",
        "selo_simnao": "¿SÍ O NO?",
        "selo_terminal": "TE ESPERO EN LA TERMINAL",
        "selo_notify": "TAREFA COMPLETADA",
        "ok": "OK",
        "fav_salvar": "Guardar este saludo en favoritos",
        "fav_salva": "Está en favoritos (clic para quitarlo)",
    },
    "fr": {
        "agente": "Agent",
        "sim": "Oui", "nao": "Non", "ja_vou": "J'arrive !",
        "agora_nao": "Pas maintenant", "responder": "Répondre", "escolher": "Choisir",
        "outra": "✏️  Écrire une autre réponse…",
        "ou_escreva": "Ou écrivez :",
        "entrada": "✏️  Ou écrivez votre réponse et appuyez sur Entrée",
        "contador": "⏳ se ferme dans {m}:{s:02d} · Échap pour fermer",
        "selo_pergunta": "QUESTION RAPIDE",
        "selo_simnao": "OUI OU NON ?",
        "selo_terminal": "JE VOUS ATTENDS DANS LE TERMINAL",
        "selo_notify": "TÂCHE TERMINÉE",
        "ok": "OK",
        "fav_salvar": "Ajouter cette accroche aux favoris",
        "fav_salva": "Dans les favoris (cliquez pour retirer)",
    },
    "de": {
        "agente": "Agent",
        "sim": "Ja", "nao": "Nein", "ja_vou": "Bin gleich da!",
        "agora_nao": "Jetzt nicht", "responder": "Antworten", "escolher": "Auswählen",
        "outra": "✏️  Andere Antwort schreiben…",
        "ou_escreva": "Oder schreiben:",
        "entrada": "✏️  Oder Antwort eingeben und Enter drücken",
        "contador": "⏳ schließt in {m}:{s:02d} · Esc schließt",
        "selo_pergunta": "KURZE FRAGE",
        "selo_simnao": "JA ODER NEIN?",
        "selo_terminal": "ICH WARTE IM TERMINAL AUF DICH",
        "selo_notify": "AUFGABE ERLEDIGT",
        "ok": "OK",
        "fav_salvar": "Diese Anrede zu den Favoriten hinzufügen",
        "fav_salva": "In den Favoriten (klicken zum Entfernen)",
    },
    "it": {
        "agente": "Agente",
        "sim": "Sì", "nao": "No", "ja_vou": "Arrivo!",
        "agora_nao": "Non ora", "responder": "Rispondi", "escolher": "Scegli",
        "outra": "✏️  Scrivi un'altra risposta…",
        "ou_escreva": "Oppure scrivi:",
        "entrada": "✏️  Oppure scrivi la risposta e premi Invio",
        "contador": "⏳ si chiude tra {m}:{s:02d} · Esc chiude",
        "selo_pergunta": "DOMANDA VELOCE",
        "selo_simnao": "SÌ O NO?",
        "selo_terminal": "TI ASPETTO NEL TERMINALE",
        "selo_notify": "TASK COMPLETATO",
        "ok": "OK",
        "fav_salvar": "Salva questo saluto nei preferiti",
        "fav_salva": "Nei preferiti (clicca per togliere)",
    },
    "ru": {
        "agente": "Агент",
        "sim": "Да", "nao": "Нет", "ja_vou": "Уже иду!",
        "agora_nao": "Не сейчас", "responder": "Ответить", "escolher": "Выбрать",
        "outra": "✏️  Написать свой ответ…",
        "ou_escreva": "Или напишите:",
        "entrada": "✏️  Или напишите ответ и нажмите Enter",
        "contador": "⏳ закроется через {m}:{s:02d} · Esc — закрыть",
        "selo_pergunta": "БЫСТРЫЙ ВОПРОС",
        "selo_simnao": "ДА ИЛИ НЕТ?",
        "selo_terminal": "ЖДУ ВАС В ТЕРМИНАЛЕ",
        "selo_notify": "ЗАДАЧА ВЫПОЛНЕНА",
        "ok": "OK",
        "fav_salvar": "Добавить это обращение в избранное",
        "fav_salva": "В избранном (нажмите, чтобы убрать)",
    },
    "zh": {
        "agente": "助手",
        "sim": "是", "nao": "否", "ja_vou": "马上来！",
        "agora_nao": "稍后再说", "responder": "回答", "escolher": "选择",
        "outra": "✏️  写下其他回答…",
        "ou_escreva": "或者输入：",
        "entrada": "✏️  或者输入你的回答并按 Enter",
        "contador": "⏳ {m}:{s:02d} 后自动关闭 · 按 Esc 关闭",
        "selo_pergunta": "快速提问",
        "selo_simnao": "是还是否？",
        "selo_terminal": "在终端等你",
        "selo_notify": "任务已完成",
        "ok": "OK",
        "fav_salvar": "把这句开场白加入收藏",
        "fav_salva": "已收藏（点击取消）",
    },
    "ja": {
        "agente": "エージェント",
        "sim": "はい", "nao": "いいえ", "ja_vou": "今行きます！",
        "agora_nao": "あとで", "responder": "回答する", "escolher": "選択",
        "outra": "✏️  別の回答を書く…",
        "ou_escreva": "または入力：",
        "entrada": "✏️  または回答を入力して Enter を押してください",
        "contador": "⏳ {m}:{s:02d} 後に自動で閉じます · Esc で閉じる",
        "selo_pergunta": "ちょっと質問",
        "selo_simnao": "はい／いいえ？",
        "selo_terminal": "ターミナルでお待ちしています",
        "selo_notify": "タスク完了",
        "ok": "OK",
        "fav_salvar": "この呼びかけをお気に入りに追加",
        "fav_salva": "お気に入り登録済み（クリックで解除）",
    },
}

# Variantes: só o que muda em relação ao idioma base.
VARIANTES = {
    "pt-PT": ("pt", {
        "entrada": "✏️  Ou escreva a sua resposta e prima Enter",
        "selo_terminal": "ESPERO POR SI NO TERMINAL",
        "selo_notify": "TAREFA CONCLUÍDA",
        "ok": "OK",
        "fav_salvar": "Guardar esta chamada nos favoritos",
        "fav_salva": "Está nos favoritos (clique para retirar)",
    }),
}
for _nome, (_base, _muda) in VARIANTES.items():
    TEXTOS[_nome] = {**TEXTOS[_base], **_muda}


def normalizar(codigo):
    """'pt_PT.UTF-8' → 'pt-PT'; 'pt_BR' → 'pt'; 'en-US' → 'en'; sem tradução ou vazio → None."""
    if not codigo:
        return None
    limpo = codigo.strip().split(":")[0].split(".")[0].split("@")[0].replace("_", "-")
    partes = limpo.split("-")
    base = partes[0].lower()
    if len(partes) > 1:
        variante = f"{base}-{partes[1].upper()}"
        if variante in TEXTOS:
            return variante
    return base if base in TEXTOS else None


def idioma_sistema():
    if sys.platform == "win32":
        try:
            import ctypes
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return locale.windows_locale.get(lcid)
        except (AttributeError, OSError):
            return None
    if sys.platform == "darwin":
        try:
            r = subprocess.run(["defaults", "read", "-g", "AppleLocale"],
                               capture_output=True, text=True, timeout=3)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    # Mesma ordem do gettext: LANGUAGE (lista, ex. "es:en") vence, LC_ALL, LC_MESSAGES, LANG.
    for parte in os.environ.get("LANGUAGE", "").split(":"):
        if normalizar(parte):
            return parte
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        valor = os.environ.get(var, "")
        if valor and valor not in ("C", "POSIX") and not valor.startswith("C."):
            return valor
    return None


def resolver(pedido=None):
    """Devolve (idioma, origem)."""
    for valor, origem in ((pedido, "--lang"), (env("POPUP_LANG", "POPUP_IDIOMA"), "POPUP_LANG")):
        if valor and valor.strip():
            if normalizar(valor):
                return normalizar(valor), origem
            return PADRAO, f"{origem} {valor.strip()} has no translation → English"
    sistema = idioma_sistema()
    if normalizar(sistema):
        return normalizar(sistema), f"system ({sistema})"
    return PADRAO, "default"


def textos(idioma):
    return TEXTOS.get(idioma, TEXTOS[PADRAO])
