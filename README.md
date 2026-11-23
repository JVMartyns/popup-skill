# popup-skill

An agent skill that asks you the task's questions through **desktop pop-up windows**
instead of the terminal, so you can work in another window and still answer.

*Leia em português: [README.pt-BR.md](README.pt-BR.md)*

| Quick question (pt-BR, favorite greeting ⭐) | Yes / no (en) | Call to the terminal (ja) |
|---|---|---|
| ![](docs/pergunta-pt.png) | ![](docs/simnao-en.png) | ![](docs/terminal-ja.png) |

## What it does

- **Three kinds of pop-up:** a direct question with option cards and a free-text field,
  a yes/no question, and a "come to the terminal" call for questions that need context.
- **Every pop-up opens with a light, friendly greeting** written by the agent for the
  moment. The question below it stays complete and serious.
- **Works across desktops.** The script picks the interface at run time:

  | System | Order tried |
  |---|---|
  | Linux (GNOME, XFCE…) | GTK4 + libadwaita → zenity → kdialog → Tkinter |
  | Linux (KDE, LXQt) | kdialog → GTK4 + libadwaita → zenity → Tkinter |
  | macOS | osascript → Tkinter |
  | Windows | Tkinter → PowerShell (WinForms) |

  No screen at all (SSH, CI) → exit 6, and the agent asks in the terminal instead.
- **10 languages for the window texts:** pt-BR, pt-PT, en, es, fr, de, it, ru, zh, ja
  (others fall back to English). The agent writes the greeting and question in *your*
  language and passes `--lang`.
- **Favorite greetings.** Keep the ones you like in a file, add them with the ⭐ in the
  window, and the script enforces the rules: no greeting repeated in a task, never two
  favorites in a row, favorites only in their own language.

## Install

### Claude Code (plugin)

```
/plugin marketplace add JVMartyns/popup-skill
/plugin install popup@popup-skill        # manual: runs only when you type /popup
# or
/plugin install popup-auto@popup-skill   # Claude may turn it on when you say you'll be away
```

Install one of the two. You can switch later with `/plugin`.

### Claude Code (plain skill folder)

```bash
git clone https://github.com/JVMartyns/popup-skill
cp -r popup-skill/skills/popup ~/.claude/skills/
```

This copy lets Claude turn it on by itself when it fits. To make it manual-only
(`/popup`), add to `~/.claude/settings.json`:

```json
{ "skillOverrides": { "popup": "user-invocable-only" } }
```

### Other agents (Codex, Gemini CLI, Cursor, Pi…)

Copy `skills/popup/` into the agent's skills folder (see its docs). If the agent does
not load skills, paste `SKILL.md` into its instructions file (`AGENTS.md`, `GEMINI.md`…)
and replace `SKILL_DIR` with the absolute path of the folder. Set `POPUP_AGENT` to the
agent's name to show it in the window title.

## Requirements

Python 3 and a graphical session. Each interface needs its own tool:
GTK4 + libadwaita + PyGObject (best look), or `zenity`, or `kdialog`, or Tkinter;
macOS and Windows use built-in `osascript` / PowerShell. Optional: `notify-send`,
`canberra-gtk-play` (sound).

Check what would be used, without opening a window:

```bash
skills/popup/popup.py doctor
```

## Usage (what the agent runs)

```bash
popup.py ask      --lang en --timeout 300 \
  --greeting "Hey, got a sec? I'm stuck on a quick choice." \
  --question "Which name should the cfg/ folder get?" \
  --option "⚙️|config|Standard name" --option "🛠️|settings|Django style"

popup.py yesno    --lang en --greeting "..." --question "Delete the 4 legacy test files?"
popup.py terminal --lang en --greeting "..." --question "Please come to the terminal: ..."
```

The answer goes to stdout (`yesno` prints `yes`/`no`, `terminal` prints `ok`). Exit codes: `0` answered, `1` closed / "Not now" / "No",
`5` timeout, `6` no screen or no interface (ask in the terminal), `7` greeting refused
(repeated or favorite rule): write another one and run again.

Options: `--lang CODE`, `--backend gtk,zenity,…` (or `POPUP_BACKEND`), `--timeout S`,
`--context TEXT`, `--no-other` (no free-text field).

Run `popup.py --help` for all options.

Coming from 0.1? The Portuguese names (`pergunta`, `simnao`, `--chamada`, `--idioma`,
`POPUP_IDIOMA`…) still work as hidden aliases, and `~/.config/popup/favoritas.txt` is
renamed to `favorites.txt` on first use. Only the `yesno` output changed: `sim`/`não`
is now `yes`/`no` (the exit code is the same).

## Favorite greetings

```bash
popup.py favorite list [--lang pt-BR]
popup.py favorite add --lang pt-BR "Chefia, me ajuda numa decisão rapidinha?"
popup.py favorite rm  --lang pt-BR "Chefia, me ajuda numa decisão rapidinha?"
```

Or click the ⭐ in the GTK window. The file lives outside the skill folder, so updates
never erase it: `~/.config/popup/favorites.txt` (Windows: `%APPDATA%\popup\favorites.txt`;
override with `POPUP_FAVORITES`). One greeting per line, in sections per language
(`[pt-BR]`, `[en]`…). Task history: `~/.local/state/popup/historico.json`
(a task ends after 2 hours without pop-ups in that folder).

## Development

`skills/popup/` is the single source. `plugins/` is generated from it:

```bash
python3 scripts/build.py          # regenerate plugins/popup and plugins/popup-auto
python3 tests/teste.py            # 69 tests, no window (fake zenity/kdialog)
```

CI runs both (`scripts/build.py --check` fails if `plugins/` is out of date).
`tests/manual/screenshot_gtk.py` renders the GTK window to a PNG.

Untested on real hardware so far: kdialog, osascript (macOS) and PowerShell (Windows).
Reports welcome.

## License

[MIT](LICENSE)
