# Testing on a new system / Testando num sistema novo

*Português abaixo.*

Use this when you try popup on a system it was not tested on yet (WSL, Windows,
macOS, KDE). It takes about 5 minutes. Please open an issue with the output.

```bash
git clone https://github.com/JVMartyns/popup-skill && cd popup-skill
P=skills/popup/popup.py        # on Windows: py skills\popup\popup.py
export POPUP_STATE_DIR=$(mktemp -d)   # keeps your real history clean

# 1. What does it detect? (no window)
$P doctor

# 2. Question with options: pick "B"
$P ask --lang en --greeting "Test 1: can you pick one?" --question "Pick B, please." \
  --option "🅰️|A|first" --option "🅱️|B|second"; echo "exit=$?"     # expect: B, exit=0

# 3. Yes/no: click No
$P yesno --lang en --greeting "Test 2: a quick one?" --question "Click No."; echo "exit=$?"   # expect: no, exit=1

# 4. Terminal call: press Esc
$P terminal --lang en --greeting "Test 3: almost done?" --question "Press Esc."; echo "exit=$?"   # expect: exit=1

# 5. Timeout: do nothing for 5 s
$P yesno --lang en --timeout 5 --greeting "Test 4: just wait?" --question "Don't click."; echo "exit=$?"   # expect: exit=5

# 6. Accents and other scripts
$P yesno --lang ja --greeting "テスト5：大丈夫ですか？" --question "Ação, ñ, ü, 中文 — all readable? Click Yes."; echo "exit=$?"
```

Report: the `doctor` output, each `exit=` line, and anything odd in the windows
(squares instead of emoji, cut text, window behind others, no sound).

**WSL:** the window should open on Windows (not through WSLg). If it does not,
rerun step 2 with `--backend zenity` and with `--backend powershell` and report both.

**Windows (native):** step 1 should show `wpf` with ✓ and `chosen: wpf`. The window
should have color emoji, follow the Windows light/dark setting, and show the cards and
the mascot. Rerun step 2 with `--backend powershell` (WinForms fallback, black-and-white
emoji) and with `--backend tkinter`. If `wpf` is ✗, report whether
`skills/popup/assets/wpf/` has the four DLLs and paste the output of
`powershell -NoProfile -Command $PSVersionTable.PSVersion`.

---

## Português

Use este roteiro quando testar o popup num sistema em que ele ainda não foi testado
(WSL, Windows, macOS, KDE). Leva uns 5 minutos. Abra uma issue com o resultado.

Rode os mesmos comandos acima. O esperado em cada passo:

| Passo | O que fazer | Esperado |
|---|---|---|
| 1. `doctor` | nada | mostra o sistema e a interface escolhida |
| 2. `ask` | escolher "B" | `B`, `exit=0` |
| 3. `yesno` | clicar em Não | `no`, `exit=1` |
| 4. `terminal` | apertar Esc | `exit=1` |
| 5. timeout | não clicar por 5 s | `exit=5` |
| 6. acentos | clicar em Sim | `yes`, `exit=0`, e todos os caracteres legíveis |

Mande a saída do `doctor`, cada linha `exit=` e qualquer coisa estranha nas janelas
(quadradinhos no lugar de emoji, texto cortado, janela atrás das outras, sem som).

**WSL:** a janela deve abrir no Windows, não pelo WSLg. Se não abrir, repita o passo 2
com `--backend zenity` e com `--backend powershell` e mande os dois resultados.

**Windows (nativo):** o passo 1 deve mostrar `wpf` com ✓ e `chosen: wpf`. A janela deve
ter emoji colorido, seguir o tema claro/escuro do Windows e mostrar os cartões e o
mascote. Repita o passo 2 com `--backend powershell` (WinForms, emoji em preto e branco)
e com `--backend tkinter`. Se `wpf` aparecer como ✗, informe se
`skills/popup/assets/wpf/` tem as quatro DLLs e mande a saída de
`powershell -NoProfile -Command $PSVersionTable.PSVersion`.
