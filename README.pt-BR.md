# popup-skill

Uma skill para agentes que faz as perguntas da tarefa por **pop-up na área de trabalho**,
em vez do terminal. Você pode trabalhar em outra janela e responder mesmo assim.

*Read in English: [README.md](README.md)*

> **Onde funciona:** agentes que rodam no seu computador, com tela, como o Claude Code
> no Linux, macOS ou Windows. **Não** funciona no claude.ai pelo navegador nem em
> ambientes na nuvem: lá não há área de trabalho para mostrar a janela.

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
  | Windows | WPF pelo PowerShell 5.1 (cartões, mascote, emoji colorido) → Tkinter → PowerShell (WinForms) |
  | WSL | janela nativa do Windows pelo `powershell.exe` (WinForms) → GTK4 → zenity → kdialog → Tkinter |

  No Windows nativo o padrão é uma janela WPF com o mesmo desenho da GTK: cartões de
  opção, mascote, emoji colorido e atalhos 1–9. Ela segue o tema claro/escuro do
  Windows. As quatro DLLs necessárias vêm dentro da skill (`assets/wpf/`, cerca de
  1,8 MB), então não há nada para o usuário instalar: o próprio PowerShell 5.1 do
  Windows abre a janela. Se as DLLs ou o PowerShell faltarem, o script cai para o
  Tkinter e depois para a janela WinForms mais simples (emoji em preto e branco).

  No WSL a janela abre no próprio Windows, então funciona sem WSLg e sem pacotes
  gráficos do Linux; o WSL continua usando a janela WinForms. Sem tela (SSH, CI) →
  exit 6, e o agente pergunta no terminal.
- **Textos da janela em 10 idiomas:** pt-BR, pt-PT, en, es, fr, de, it, ru, zh, ja
  (os outros saem em inglês). O agente escreve a chamada e a pergunta no *seu* idioma e
  passa `--lang`.
- **Chamadas favoritas.** Guarde as que você gosta num arquivo ou com a ⭐ da janela. O
  agente alterna as favoritas com chamadas novas, e o script aplica as regras: nenhuma chamada repetida na tarefa, nunca duas favoritas
  seguidas, favorita só no idioma dela.

## Instalação

### Claude Code (plugin)

```
/plugin marketplace add JVMartyns/popup-skill
/plugin install popup@popup-skill        # manual: só roda quando você digita /popup (nome completo: /popup:popup)
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
rodar com `/popup`, acrescente em `~/.claude/settings.json` (ou no `.claude/settings.json` do projeto):

```json
{ "skillOverrides": { "popup": "user-invocable-only" } }
```

### Cursor

Clone o repositório e linke a skill na pasta de skills do Cursor:

```bash
git clone https://github.com/JVMartyns/popup-skill
mkdir -p ~/.cursor/skills
ln -sfn "$PWD/popup-skill/skills/popup" ~/.cursor/skills/popup
```

Para instalar só num projeto, use `.cursor/skills/` na raiz do projeto. Para copiar
em vez de linkar: `cp -r popup-skill/skills/popup ~/.cursor/skills/`. No Windows, a
pasta é `%USERPROFILE%\.cursor\skills\popup`.

Recarregue a janela do Cursor (`Ctrl+Shift+P` → **Developer: Reload Window**) e, no
chat, digite `/popup` e o pedido.

No Cursor Flatpak, o shell do agente roda dentro do sandbox, onde GTK/PyGObject e
Tkinter normalmente não estão disponíveis; o zenity está, então a janela cai na
versão de lista simples. Fora do Flatpak, a janela GTK é usada.

### Outros agentes (Codex, Gemini CLI, Pi…)

Copie `skills/popup/` para a pasta de skills do agente (veja a documentação dele). Se
ele não carregar skills, cole o `SKILL.md` nas instruções dele (`AGENTS.md`,
`GEMINI.md`…) e troque `SKILL_DIR` pelo caminho absoluto da pasta. Defina `POPUP_AGENT`
com o nome do agente para ele aparecer no título da janela.

### Atualizar

A versão do plugin fica em `plugins/*/.claude-plugin/plugin.json`; o Claude Code
só baixa uma cópia nova quando essa versão muda.

O auto-update vem **desligado por padrão** em marketplaces de comunidade. Para o
Claude Code atualizar no início da sessão, abra `/plugin` → **Marketplaces** →
`popup-skill` e ligue o auto-update.

Para atualizar à mão:

```bash
claude plugin marketplace update popup-skill
claude plugin update popup@popup-skill      # ou popup-auto@popup-skill
```

Dentro de uma sessão, `/plugin` → **Installed** → selecione o plugin → **Update now**;
depois rode `/reload-plugins` ou inicie outra sessão. `/plugin list` mostra a
versão instalada.

Se você copiou a pasta da skill à mão (`git clone` + `cp`), atualize com
`git pull` no clone e copie `skills/popup/` de novo.

Confira a versão que o script está rodando:

```bash
$POPUP --version      # ou: $POPUP doctor
```

## Requisitos

Python 3 e uma sessão gráfica. Cada interface precisa da sua ferramenta:
GTK4 + libadwaita + PyGObject (o visual mais completo), ou `zenity`, ou `kdialog`, ou
Tkinter; macOS e Windows usam `osascript` / PowerShell, que já vêm no sistema. No
Windows, a janela WPF usa as DLLs incluídas em `skills/popup/assets/wpf/` e o
PowerShell 5.1, ambos já presentes; a alternativa WinForms só precisa do PowerShell.
Opcionais: `popup.py notify`, `canberra-gtk-play` (som).

Para ver o que seria usado, sem abrir janela:

```bash
skills/popup/popup.py doctor
```

## Uso (o que o agente roda)

Você não digita estes comandos: o agente roda, com o caminho completo que o `SKILL.md`
dá a ele. Para rodar o script você mesmo, veja [Rodando o script você mesmo](#rodando-o-script-você-mesmo).

```bash
popup.py ask      --lang pt-BR --timeout 300 \
  --greeting "Opa, tem um minutinho? Empaquei numa escolha." \
  --question "Qual nome dou para a pasta cfg/?" \
  --option "⚙️|config|Nome padrão" --option "🛠️|settings|Estilo Django"

popup.py yesno    --lang pt-BR --greeting "..." --question "Apago os 4 testes antigos?"
popup.py terminal --lang pt-BR --greeting "..." --question "Preciso de você no terminal: ..."
```

A resposta sai no stdout (`yesno` imprime `yes`/`no`, `terminal` imprime `ok`). Exit: `0` respondeu, `1` fechou / "Agora não" / "Não",
`5` timeout, `6` sem tela ou sem interface (pergunte no terminal), `7` chamada recusada
(repetida ou regra de favorita): escreva outra e rode de novo.

Opções: `--lang CÓDIGO`, `--backend gtk,zenity,…` (ou `POPUP_BACKEND`),
`--timeout S`, `--context TEXTO`, `--no-other` (sem campo para escrever).

`popup.py --help` mostra todas as opções.

Vindo da 0.1? Os nomes em português (`pergunta`, `simnao`, `--chamada`, `--idioma`,
`POPUP_IDIOMA`…) continuam funcionando como apelidos escondidos, e
`~/.config/popup/favoritas.txt` vira `favorites.txt` no primeiro uso. Só a saída do
`yesno` mudou: `sim`/`não` agora é `yes`/`no` (o exit code é o mesmo).

## Chamadas favoritas

O jeito mais fácil é pedir ao agente: *"guarda essa chamada nas favoritas"*, *"mostra
minhas favoritas"*. Ele já sabe onde está o script. Ou clique na ⭐ da janela GTK ou
WPF.
Pelo terminal (veja `$POPUP` na próxima seção):

```bash
$POPUP favorite list [--lang pt-BR]
$POPUP favorite add --lang pt-BR "Chefia, me ajuda numa decisão rapidinha?"
$POPUP favorite rm  --lang pt-BR "Chefia, me ajuda numa decisão rapidinha?"
```

O arquivo fica fora da pasta da skill, para não ser
apagado nas atualizações: `~/.config/popup/favorites.txt` (Windows:
`%APPDATA%\popup\favorites.txt`; dá para trocar com `POPUP_FAVORITES`). Uma chamada por
linha, em seções por idioma (`[pt-BR]`, `[en]`…). Histórico das tarefas:
`~/.local/state/popup/historico.json` (uma tarefa termina depois de 2 horas sem pop-up
naquela pasta).

## Rodando o script você mesmo

O script não está no seu `PATH`. O lugar depende de como você instalou:

```bash
# plugin (o nome da pasta muda com a versão)
POPUP=$(ls -d ~/.claude/plugins/cache/popup-skill/*/*/skills/popup | sort -V | tail -1)/popup.py
# pasta de skill
POPUP=~/.claude/skills/popup/popup.py

$POPUP doctor     # qual interface e idioma seriam usados, sem abrir janela
$POPUP --help
```

## O que roda e grava na sua máquina

Tudo fica no seu computador. A skill **não acessa a rede** e não coleta dados. Veja
[PRIVACY.md](PRIVACY.md).

- **Roda:** Python 3; uma ferramenta de diálogo da tabela acima (GTK pelo PyGObject,
  `zenity`, `kdialog`, `osascript`, `powershell` — no Windows e no WSL, o
  `powershell.exe` — ou Tkinter); `git branch --show-current`
  para mostrar a branch no título da janela; opcionalmente `canberra-gtk-play` (Linux),
  `afplay` (macOS) ou um bipe do sistema (Windows) para o som. O agente também pode rodar
  `notify-send` quando uma pergunta fica sem resposta. No Windows nativo, a janela WPF
  carrega as DLLs de `skills/popup/assets/wpf/` no PowerShell.
- **Grava:** `~/.config/popup/favorites.txt` (suas chamadas favoritas) e
  `~/.local/state/popup/historico.json` (chamadas mostradas em cada pasta de trabalho,
  guardadas por 2 horas para aplicar as regras de repetição). No Windows:
  `%APPDATA%\popup\` e `%LOCALAPPDATA%\popup\`. A janela WPF grava o `.ps1` gerado
  (UTF-8 com BOM) e, quando você clica na ⭐, um pequeno arquivo de controle na pasta
  temporária do usuário; os dois são apagados logo depois que a janela fecha. A
  alternativa WinForms não grava arquivo: o script da janela e os textos vão direto no
  comando (`-EncodedCommand`).
- **Lê:** as variáveis de ambiente listadas acima, o idioma do sistema e esses dois arquivos.

## Desenvolvimento

`skills/popup/` é a fonte única. `plugins/` é gerado a partir dela:

```bash
python3 scripts/build.py          # gera plugins/popup e plugins/popup-auto
python3 tests/teste.py            # 123 testes, sem janela (zenity/kdialog/powershell falsos)
```

O CI roda os dois (`scripts/build.py --check` falha se `plugins/` estiver desatualizado).
`tests/manual/screenshot_gtk.py` desenha a janela GTK num PNG. Os testes do WPF simulam
o Windows nativo (`popup.WINDOWS = True`) e conferem o `.ps1` gerado, os dados/XAML da
janela, a ordem das DLLs, as alternativas e a saída do `doctor`; não abrem janela.

Testados em máquina real: GNOME (GTK e zenity) e WSL (janela nativa do Windows,
WinForms). A janela WPF foi feita a partir do preview aprovado, mas ainda não rodou em
Windows nativo de verdade. Ainda não testados: kdialog, osascript (macOS) e
WPF/Tkinter no Windows nativo. Se você puder testar algum, o
[docs/TESTING.md](docs/TESTING.md) tem um roteiro de 5 minutos. Relatos são bem-vindos.

## Licença

[MIT](LICENSE)
