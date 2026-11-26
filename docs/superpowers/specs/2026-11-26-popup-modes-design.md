# Modos de apresentação: window, dialog e notification

## Contexto

Hoje o `popup.py` escolhe a interface sozinho (`ordem_padrao`, `popup.py:236-247`):
GTK/WPF (janela própria) quando disponível, senão zenity/kdialog/osascript
(diálogos nativos). O usuário não tem como dizer "prefiro diálogo" ou "não quero
nada pulando na tela".

O pedido: assim como existem as favoritas, existir um arquivo de preferências do
usuário para escolher entre três formas de chamar a atenção:

- **window** (padrão): a janela própria de hoje.
- **dialog**: um diálogo, com as mesmas funcionalidades da janela.
- **notification**: um aviso pequeno, de mão única, para conclusão de tarefa ou
  chamada ao terminal.

O agente lê a preferência e as favoritas antes de montar cada chamada.

## Decisões do usuário

- O padrão é **window**.
- Os três tipos de chamada são: dúvida (`ask`/`yesno`), aviso de conclusão
  (`notify`) e chamada ao terminal (`terminal`).
- **notification não devolve resposta.** Serve para avisos de conclusão e
  chamadas ao terminal. Perguntas, nesse modo, são feitas no terminal.
- O usuário pode não gostar da janela e preferir o diálogo; o diálogo precisa
  oferecer as mesmas funcionalidades da janela.
- O agente lê a preferência do usuário e as favoritas antes de decidir como
  chamar a atenção.

## Decisões de projeto (minhas)

- **Um único modo** (`window|dialog|notification`), não duas preferências
  separadas. É o modelo que o usuário descreveu ("escolher entre os 3").
- Arquivo `preferences.txt` no mesmo diretório das favoritas:
  `~/.config/popup/preferences.txt` (Windows: `%APPDATA%\popup\preferences.txt`),
  override `POPUP_PREFERENCES`.
- Formato `chave = valor`, comentários com `#`, por enquanto só `mode`:
  ```
  # popup preferences
  mode = window
  ```
- Precedência: `--mode` > `POPUP_MODE` > arquivo > `window`.
- `--backend` continua existindo, mas só escolhe o backend **dentro** do modo;
  não muda o comportamento do modo. Para forçar uma janela em modo notification,
  o usuário passa `--mode window --backend zenity`.
- Comando novo `preference`:
  - `popup.py preference` → imprime só o modo efetivo (`window`), para o agente ler.
  - `popup.py preference list` → `mode = window`, a origem (`file`/`env`/`default`)
    e o caminho do arquivo.
  - `popup.py preference set dialog` → valida, grava e imprime o modo efetivo.
    Se `POPUP_MODE` estiver definido e vencer o arquivo, avisa no stderr que o
    arquivo foi gravado mas o ambiente continua mandando; o agente não deve
    reportar sucesso enganoso.
  - Alias em português `preferencia` (mesmo padrão dos apelidos da 0.1).
- Comando novo `notify`: aviso de conclusão. Em window/dialog mostra um popup
  com um único botão OK e fecha sozinho (padrão 20 s). Em notification manda a
  notificação e sai na hora.
- Em notification, `ask`/`yesno` saem com **exit 6** e uma mensagem no stderr
  ("notification mode: ask in the terminal"). Não abrem nada. O agente pergunta
  no terminal e usa `terminal` para avisar.
- Em notification, `terminal` e `notify` usam o notificador do sistema e saem
  com 0. Não tocam som e não bloqueiam.
- O `notify` também segue as regras de favoritas (chamada nova, sem repetir,
  favorita só no idioma dela), porque a chamada aparece no aviso.

## Comportamento por modo

| comando | window | dialog | notification |
|---|---|---|---|
| `ask` | janela | diálogo | exit 6 (perguntar no terminal) |
| `yesno` | janela | diálogo | exit 6 (perguntar no terminal) |
| `terminal` | janela | diálogo | notificação (urgência crítica), exit 0 |
| `notify` | janela com OK | diálogo com OK | notificação (urgência normal), exit 0 |

O diálogo oferece o mesmo conteúdo da janela: chamada, pergunta, contexto,
cartões de opção, campo de resposta livre, sim/não, contador, som, ⭐ de
favorita e Esc. O que muda é a apresentação e o comportamento de flutuação.

## Preferência do usuário

### Arquivo

- Caminho: `pasta_config()/preferences.txt`, reutilizando `favoritas.pasta_config()`.
- Leitura tolerante: arquivo ausente → `window`; linha inválida → aviso no
  stderr e `window`; chave desconhecida → ignora (reservado para o futuro).
- Gravação atômica (arquivo temporário + `os.replace`) e criação do diretório.
- O arquivo fica fora da pasta da skill, para sobreviver a atualizações.

### Módulo novo `skills/popup/preferencias.py`

Responsabilidades:

- `MODOS = ("window", "dialog", "notification")`
- `caminho()` → caminho do arquivo (respeita `POPUP_PREFERENCES`).
- `ler()` → dicionário de chaves (ou só o modo).
- `modo()` → modo efetivo, com precedência e validação.
- `gravar(modo)` → valida e grava.
- `origem()` → `"flag" | "env" | "file" | "default"`, para o `doctor`.

Não importa `popup.py`; pode importar `favoritas.pasta_config` e `textos.env`.

## Comandos e flags

### `popup.py`

- `MODOS` ganha `"notify": "notificacao"` e `"preference": "preferencia"`.
- `cmd_preferencia(p, a)`:
  - sem `extra` → imprime o modo.
  - `list` → imprime `mode = ...`, a origem e o caminho.
  - `set MODE` → valida, grava e imprime o modo efetivo (com o aviso de
    `POPUP_MODE`, como acima).
  - valor inválido → `p.error(...)` (exit 2).
- `--mode` global, `choices=preferencias.MODOS`.
- `POPUP_MODE` lido por `preferencias.modo()`.
- `--timeout` continua global; para `notify`, se o usuário não passou
  `--timeout`, o padrão efetivo é 20 s. Em window/dialog, `notify` fecha no OK,
  no Esc ou no timeout e sai com 0 em todos os backends; `terminal` mantém o
  timeout 5.
- `notify` exige `--greeting`; `--question` e `--context` são opcionais (o aviso
  de conclusão é uma frase, não uma pergunta). `ask`/`yesno` continuam exigindo
  `--greeting` e `--question`.
- O modo é resolvido antes de escolher o backend. Se `notification` e o comando
  for `pergunta`/`simnao`, aviso + exit 6 **antes** da checagem de favoritas (a
  chamada não vai aparecer, então não faz sentido recusá-la por repetição).
  Para `terminal`/`notify` em notification, as favoritas continuam valendo.
- `notify`/`terminal` em notification chamam `notificacao.enviar(a, urgente=...)`
  e saem com 0.
- `doctor` mostra `mode: window (from file)`, o caminho e o notificador que
  seria usado.

### `notificacao.py` (novo)

- `disponivel()` → há um notificador para a plataforma?
- `enviar(a, urgente=False)` → escolhe o backend e devolve `True`/`False`.
- Título: `titulo_janela()` (✨ Agente · pasta · branch).
- Corpo: `texto(a)` (chamada + pergunta + contexto).
- Linux: `notify-send --app-name=Popup --icon=<mascote.svg> --urgency=normal|critical`.
- macOS: `osascript -e 'display notification ... with title ...'` (sem som).
- Windows/WSL: PowerShell com `System.Windows.Forms.NotifyIcon` (balloon tip),
  ícone de informação, 5 s, processo encerra sozinho depois de ~6 s.
- Se o notificador falhar: aviso no stderr e exit 6, sem fallback automático
  (ver "Casos de borda").
- Sem tela: não chama `tem_tela()` antes; deixa o notificador tentar. Se falhar,
  exit 6.

## Interface GTK: janela e diálogo

`ui_gtk.py` ganha `--apresentacao {window,dialog}` (padrão `window`).
`popup.py` passa o valor em `ui_gtk(a)`.

### Refatoração da montagem

Hoje `raiz` = header + corpo, e `self.win.set_content(raiz)`. Separar:

- `corpo`: o box com mascote, textos, opções, entrada e rodapé.
- `selo` e `botao_favorita()`: vão para o header.

### window (atual)

- `Adw.ApplicationWindow(application=self, title=titulo_janela())`.
- `Adw.HeaderBar` com o selo como título e a ⭐ no fim.
- `raiz` com `.popup-bg`, header + corpo; `set_content(raiz)`.
- Sem mudanças visuais.

### dialog

- `Gtk.Dialog(application=self, title=titulo_janela())`.
- `set_modal(True)` — é o que faz flutuar no PaperWM em vez de ocupar um tile.
- `set_default_size(620, -1)`, `set_resizable(False)`.
- Header nativo: `get_header_bar()`; título = selo; `pack_end(botao_favorita())`.
- `set_show_title_buttons(False)` para não duplicar o botão de fechar; o
  fechamento continua no rodapé ("Agora não"/"Não") e no Esc.
- `get_content_area().append(wrapper)` com o corpo e `.popup-bg`.
- Se `get_header_bar()` devolver `None` (tema/versão sem header bar), cair para
  um `Adw.HeaderBar` dentro do conteúdo, como no window.
- `Gtk.Dialog` está deprecado no GTK 4.10+, mas funciona e é o que o patch do
  usuário validou. Um follow-up pode trocar por `Gtk.Window` modal + transient
  se o aviso de deprecação incomodar.
- O diálogo mantém: cartões, entrada livre, sim/não, contador, som, ⭐, Esc,
  timeout e os mesmos exit codes.

### notification

Não usa GTK. `ui_gtk` não é chamado.

## Outros backends

### zenity / kdialog / osascript

- Já são diálogos; em window e dialog continuam iguais.
- `notify`: zenity `--info` com `--ok-label=OK`; kdialog `--msgbox`; osascript
  `display dialog` com um botão.
- Em notification não são usados.

### WPF (Windows)

- O WPF já chama `ShowDialog()` (`wpf.ps1:210`), então window e dialog são o
  mesmo cartão flutuante. A diferença visual entre os dois é pequena no Windows;
  documentar isso.
- `notify`: novo modo no template, com selo "TAREFA CONCLUÍDA", um botão OK e
  timeout de 20 s; OK, Esc e timeout saem com 0.
- `window`/`dialog` seguem com o cartão atual; `dialog` não precisa de mudança
  funcional.

### PowerShell/WinForms (fallback Windows/WSL)

- `PS_FORM` ganha o modo `notify`: selo, um botão OK, sem campo de texto;
  timeout de 20 s e OK/Esc/timeout saem com 0.
- `terminal` e `simnao` continuam como estão.
- Em window e dialog o Form é o mesmo; `ShowDialog()` já é modal.

### tkinter

- `notify`: mostra o cartão com um botão OK, timeout de 20 s e exit 0 em
  OK/Esc/timeout.
- `window` e `dialog` continuam iguais (tkinter não tem um diálogo nativo
  distinto); documentar que é fallback.

### macOS

- `osascript` é o diálogo nativo; window e dialog usam o mesmo.
- notification: `display notification` via osascript.

## Textos

`textos.py` ganha, nos 10 idiomas:

- `selo_notify`: "TAREFA CONCLUÍDA" / "TASK DONE" / equivalentes.
- `ok`: "OK" (igual em todos, mas centralizado para consistência).

Nada mais muda nas traduções existentes.

## Agente (SKILL.md)

Antes de cada chamada, o agente passa a fazer:

1. `SKILL_DIR/popup.py preference` → `window`, `dialog` ou `notification`.
2. `SKILL_DIR/popup.py favorite list --lang <código>` (como hoje).
3. Monta a chamada conforme o modo:
   - `window`/`dialog`: `ask`, `yesno`, `terminal` ou `notify` normalmente; o
     script aplica a apresentação.
   - `notification`: não chama `ask`/`yesno`. Pergunta no terminal e chama
     `terminal` com um resumo de uma linha para avisar. Ao concluir a tarefa,
     chama `notify`.
4. Se o usuário pedir para trocar ("prefiro diálogo", "só notificação"), o
   agente roda `popup.py preference set <modo>`.
5. O bloco antigo de `notify-send` cru em "Sem resposta" é removido: o agente
   usa `popup.py notify` (ou `terminal`) para não duplicar aviso e para passar
   pelas favoritas, título e ícone.

O script também lê a preferência sozinho; a leitura pelo agente serve para ele
decidir **se** pode perguntar por popup ou se deve perguntar no terminal.

## Casos de borda

- Arquivo ausente → window (comportamento atual).
- Valor inválido no arquivo → aviso + window.
- `--mode` inválido → erro do argparse (exit 2).
- `POPUP_MODE` inválido → aviso + arquivo/default.
- `--backend` desconhecido → aviso e ignora, como hoje.
- `ask`/`yesno` em notification → exit 6, sem abrir backend.
- `notify`/`terminal` em notification sem notificador → aviso no stderr e
  **exit 6**, sem abrir popup automaticamente. O contrato é fire-and-forget: um
  fallback modal poderia prender o shell por até 300 s e contrariar a escolha
  do usuário. Se quiser, o agente repete com `--mode window`.
- `notify` em window/dialog com OK, Esc ou timeout → exit 0; `terminal` com
  timeout → exit 5, como hoje.
- Sem tela em window/dialog → exit 6, como hoje.
- Favorita repetida/duas seguidas → exit 7, como hoje, inclusive em `notify`.
- O modo pode mudar no meio da tarefa; o agente relê antes de cada chamada.

## Testes

- `tests/bin/notify-send` falso (wrapper do `fake.py`) para registrar argv.
- Preferências:
  - padrão window sem arquivo;
  - `preference set dialog` grava e `preference` lê;
  - `preference set inválido` → exit 2;
  - arquivo inválido → window + aviso;
  - `POPUP_MODE` e `--mode` com precedência correta.
- Notification:
  - `notify --mode notification` chama `notify-send` com título/corpo e exit 0;
  - `terminal --mode notification` usa urgência crítica;
  - `ask`/`yesno --mode notification` → exit 6 e nenhum backend chamado;
  - notificador ausente → exit 6 com aviso e nenhum backend chamado.
- Dialog:
  - `ask --mode dialog --backend zenity` continua funcionando (zenity já é
    diálogo);
  - construção do comando GTK com `--apresentacao dialog` (teste unitário ou
    inspeção do argv via fake);
  - manual: `tests/manual/screenshot_gtk.py` ganha uma variante dialog para
    conferir no PaperWM.
- WPF/PowerShell: teste manual no Windows/WSL; o `ShowDialog()` já é modal.
- Rodar `scripts/build.py --check` e a suíte inteira.

## Documentação e build

- `README.md` e `README.pt-BR.md`: seção "Preferências", os três modos, o
  comando `preference`, o `notify`, o comportamento de notification e o arquivo
  gravado. Atualizar requisitos (notify-send opcional, balloon no Windows).
- `SKILL.md` (fonte) e, via `scripts/build.py`, as duas cópias em `plugins/`.
- `popup.py --help` e docstring.
- `VERSION` → `0.5.0` (recurso novo, compatível).
- `scripts/build.py` não muda; rodar para regenerar `plugins/`.

## Não-objetivos

- Notificação com ações/botões ou clique que abre a janela (não é portável e o
  usuário disse que não precisa de resposta).
- Duas preferências separadas (perguntas/avisos); o modelo é um modo só.
- Reescrever as favoritas ou o histórico.
- Novos idiomas.
- Trocar o backend padrão de window; o comportamento atual continua sendo o
  padrão.

## Decisões resolvidas na revisão (builder check)

- **Notificador falhou em notification:** aviso no stderr e exit 6, sem popup
  automático; o agente pode repetir com `--mode window` se o usuário quiser.
- **`notify` exige `--question`?** Não; exige `--greeting`, e `--question`/
  `--context` são opcionais. O corpo usa só as partes preenchidas.
- **`preference set` com `POPUP_MODE`:** grava o arquivo, imprime o modo
  efetivo e avisa que o ambiente ainda vence.
- **Ordem em notification:** `ask`/`yesno` saem com 6 antes da checagem de
  favoritas; `terminal`/`notify` continuam passando por ela.
- **Timeout do `notify`:** 20 s, exit 0 em OK/Esc/timeout em todos os backends;
  `terminal` mantém exit 5 no timeout.
- **`notify-send` cru no SKILL.md:** substituído por `popup.py notify`/
  `terminal`; o comando novo é o único caminho de notificação.
- **`notify` em window/dialog:** fecha sozinho em 20 s, com OK opcional.
- **Corpo da notificação:** o mesmo `texto(a)` da janela (chamada + pergunta +
  contexto, só as partes preenchidas).
- **`ask`/`yesno` em notification:** não mandam notificação automática; o
  agente chama `terminal`.
- **Windows:** balloon tip (NotifyIcon) em vez de toast WinRT, por não exigir
  registro de AppID nem módulo extra; toast fica para o futuro.
