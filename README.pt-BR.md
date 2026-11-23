# popup-skill

Uma skill para agentes que faz as perguntas da tarefa por **pop-up na área de trabalho**,
em vez do terminal. Você pode trabalhar em outra janela e responder mesmo assim.

*Read in English: [README.md](README.md)*

| Pergunta rápida (pt-BR, chamada favorita ⭐) | Sim ou não (en) | Chamada ao terminal (ja) |
|---|---|---|
| ![](docs/pergunta-pt.png) | ![](docs/simnao-en.png) | ![](docs/terminal-ja.png) |

## O que faz

- **Três tipos de pop-up:** pergunta direta com cartões de opção e campo para escrever,
  sim ou não, e "venha ao terminal" para dúvidas que precisam de contexto.
- **Todo pop-up abre com uma chamada leve e simpática**, escrita pelo agente para o
  momento. A pergunta logo abaixo vem inteira e séria.
- **Funciona em vários desktops.** O script escolhe a interface na hora:

  | Sistema | Ordem das tentativas |
  |---|---|
  | Linux (GNOME, XFCE…) | GTK4 + libadwaita → zenity → kdialog → Tkinter |
  | Linux (KDE, LXQt) | kdialog → GTK4 + libadwaita → zenity → Tkinter |
  | macOS | osascript → Tkinter |
  | Windows | Tkinter → PowerShell (WinForms) |

  Sem tela (SSH, CI) → exit 6, e o agente pergunta no terminal.
- **Textos da janela em 10 idiomas:** pt-BR, pt-PT, en, es, fr, de, it, ru, zh, ja
  (os outros saem em inglês). O agente escreve a chamada e a pergunta no *seu* idioma e
  passa `--idioma`.
- **Chamadas favoritas.** Guarde as que você gosta num arquivo ou com a ⭐ da janela. O
  script aplica as regras: nenhuma chamada repetida na tarefa, nunca duas favoritas
  seguidas, favorita só no idioma dela.

## Instalação

### Claude Code (plugin)

```
/plugin marketplace add JVMartyns/popup-skill
/plugin install popup@popup-skill        # manual: só roda quando você digita /popup
# ou
/plugin install popup-auto@popup-skill   # o Claude pode ativar quando você disser que vai sair
```

Instale um dos dois. Dá para trocar depois pelo `/plugin`.

### Claude Code (pasta de skill)

```bash
git clone https://github.com/JVMartyns/popup-skill
cp -r popup-skill/skills/popup ~/.claude/skills/
```

Essa cópia deixa o Claude ativar a skill sozinho quando fizer sentido. Para ela só
rodar com `/popup`, acrescente em `~/.claude/settings.json`:

```json
{ "skillOverrides": { "popup": "user-invocable-only" } }
```

### Outros agentes (Codex, Gemini CLI, Cursor, Pi…)

Copie `skills/popup/` para a pasta de skills do agente (veja a documentação dele). Se
ele não carregar skills, cole o `SKILL.md` nas instruções dele (`AGENTS.md`,
`GEMINI.md`…) e troque `SKILL_DIR` pelo caminho absoluto da pasta. Defina `POPUP_AGENTE`
com o nome do agente para ele aparecer no título da janela.

## Requisitos

Python 3 e uma sessão gráfica. Cada interface precisa da sua ferramenta:
GTK4 + libadwaita + PyGObject (o visual mais completo), ou `zenity`, ou `kdialog`, ou
Tkinter; macOS e Windows usam `osascript` / PowerShell, que já vêm no sistema.
Opcionais: `notify-send`, `canberra-gtk-play` (som).

Para ver o que seria usado, sem abrir janela:

```bash
skills/popup/popup.py diagnostico
```

## Uso (o que o agente roda)

```bash
popup.py pergunta --idioma pt-BR --timeout 300 \
  --chamada "Opa, tem um minutinho? Empaquei numa escolha." \
  --pergunta "Qual nome dou para a pasta cfg/?" \
  --opcao "⚙️|config|Nome padrão" --opcao "🛠️|settings|Estilo Django"

popup.py simnao   --idioma pt-BR --chamada "..." --pergunta "Apago os 4 testes antigos?"
popup.py terminal --idioma pt-BR --chamada "..." --pergunta "Preciso de você no terminal: ..."
```

A resposta sai no stdout. Exit: `0` respondeu, `1` fechou / "Agora não" / "Não",
`5` timeout, `6` sem tela ou sem interface (pergunte no terminal), `7` chamada recusada
(repetida ou regra de favorita): escreva outra e rode de novo.

Opções: `--idioma CÓDIGO`, `--backend gtk,zenity,…` (ou `POPUP_BACKEND`),
`--timeout S`, `--contexto TEXTO`, `--sem-outra` (sem campo para escrever).

## Chamadas favoritas

```bash
popup.py favorita list [--idioma pt-BR]
popup.py favorita add --idioma pt-BR "Chefia, me ajuda numa decisão rapidinha?"
popup.py favorita rm  --idioma pt-BR "Chefia, me ajuda numa decisão rapidinha?"
```

Ou clique na ⭐ da janela GTK. O arquivo fica fora da pasta da skill, para não ser
apagado nas atualizações: `~/.config/popup/favoritas.txt` (Windows:
`%APPDATA%\popup\favoritas.txt`; dá para trocar com `POPUP_FAVORITAS`). Uma chamada por
linha, em seções por idioma (`[pt-BR]`, `[en]`…). Histórico das tarefas:
`~/.local/state/popup/historico.json` (uma tarefa termina depois de 2 horas sem pop-up
naquela pasta).

## Desenvolvimento

`skills/popup/` é a fonte única. `plugins/` é gerado a partir dela:

```bash
python3 scripts/build.py          # gera plugins/popup e plugins/popup-auto
python3 tests/teste.py            # 63 testes, sem janela (zenity/kdialog falsos)
```

O CI roda os dois (`scripts/build.py --check` falha se `plugins/` estiver desatualizado).
`tests/manual/screenshot_gtk.py` desenha a janela GTK num PNG.

Ainda não testados em máquina real: kdialog, osascript (macOS) e PowerShell (Windows).
Relatos são bem-vindos.

## Licença

[MIT](LICENSE)
