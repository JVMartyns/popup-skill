---
name: popup
description: Ask the user the task's questions through desktop pop-up windows (Linux GTK/KDE, macOS, Windows) instead of the terminal. Runs only when the user invokes it with /popup.
disable-model-invocation: true
---

# Perguntas por pop-up

O usuário pediu que, nesta tarefa, as dúvidas cheguem por pop-up na tela,
ou avisou que vai estar em outra janela. Vale até o fim da tarefa ou até ele pedir para parar.
Se o pedido veio junto com uma tarefa, execute essa tarefa com esta regra.

## Requisitos

Python 3 e uma sessão gráfica. O script escolhe a interface na hora, pela ordem:

| Sistema | Ordem das interfaces |
|---|---|
| Linux (GNOME, XFCE etc.) | GTK4 + libadwaita → `zenity` → `kdialog` → Tkinter |
| Linux (KDE, LXQt) | `kdialog` → GTK4 + libadwaita → `zenity` → Tkinter |
| macOS | `osascript` → Tkinter |
| Windows | Tkinter → PowerShell (WinForms) |
| WSL (Linux no Windows) | janela nativa do Windows pelo `powershell.exe` → GTK4 → `zenity` → `kdialog` → Tkinter |

Ele usa a primeira que estiver instalada e abrir. Se uma quebrar, tenta a próxima.
Só a GTK mostra cartões, mascote e atalhos 1-9 completos; as outras mostram uma lista simples.

## Caminhos

Nos comandos abaixo, `SKILL_DIR` é a pasta onde este `SKILL.md` está
(no Claude Code: `${CLAUDE_SKILL_DIR}`).
Substitua pelo caminho absoluto antes de rodar.

Defina `POPUP_AGENT` com o nome do agente (ex.: `Codex`, `Gemini CLI`) para ele
aparecer no título da janela. Sem a variável, o título mostra "Agente".

Para ver qual interface e qual idioma seriam usados, sem abrir janela:

```bash
SKILL_DIR/popup.py doctor
```

Para forçar uma interface (ou uma ordem), use `--backend` ou `POPUP_BACKEND`:
`gtk`, `zenity`, `kdialog`, `osascript`, `powershell`, `tkinter`
(ex.: `POPUP_BACKEND=zenity,tkinter`).

## Idioma

Escreva a chamada, a pergunta, o contexto e as opções no idioma da **última mensagem
do usuário**. Nunca use o idioma deste SKILL.md (português) nem o das suas instruções
de sistema. Se o usuário escreve em russo, tudo no pop-up sai em russo.

Use também a **variante** do usuário. Português de Portugal não é português do
Brasil: se ele escreve "ficheiro", "base de dados", "ecrã", "consegues", escreva assim
também, sem gírias brasileiras. O mesmo vale para espanhol da Espanha e da América
Latina, inglês britânico e americano etc.

Passe o idioma em `--lang` em **todo** pop-up, com o código do idioma da conversa:
`pt-BR`, `pt-PT`, `en`, `es`, `fr`, `de`, `it`, `ru`, `zh`, `ja` ou outro código
ISO 639-1 (ex.: `ko`, `ar`). Os botões e o contador saem nesse idioma. Se ele não
tiver tradução no script, os botões saem em inglês; os seus textos continuam no
idioma do usuário.

### Termos técnicos

A chamada não leva termo técnico (veja "Chamada engraçada"). Na pergunta, no
contexto e nas opções:

- **Nunca traduza** o que o usuário pode digitar ou procurar: nome de arquivo, pasta,
  função, variável, comando, flag, branch, pacote, produto e mensagem de erro.
  Escreva igual ao original.
- **Termo técnico do dia a dia** (deploy, merge, commit, branch, pull request): use a
  forma que o usuário usa na conversa. Se ele não usou nenhuma, mantenha em inglês.
- **Palavra comum** (pasta, banco de dados, arquivo de teste): traduza para o idioma
  da conversa.

Exemplo em espanhol: "¿Hago el merge de la branch feature/login en main?"

A saída não muda com o idioma: `yesno` sempre imprime `yes`/`no` e `terminal`
imprime `ok`. Decida pelo exit code.

## Quando perguntar por pop-up

Sempre que você faria uma pergunta ao usuário, escolha o estilo:

1. **Pergunta direta (padrão):** decisões com poucas alternativas (nome, formato, "A ou B?").
   A pergunta vai inteira na janela, com opções em cartões e um campo para escrever a resposta.
2. **Chamada ao terminal:** dúvidas que precisam de contexto (trecho de código,
   comparar abordagens, pedir revisão). O pop-up só chama o usuário; escreva a pergunta
   completa no terminal antes de abrir a janela.

## Chamada engraçada

Todo pop-up abre com uma chamada engraçada. A pergunta vem logo abaixo, inteira e
séria: a graça fica só na primeira linha.

Não repita uma chamada já usada na tarefa.
Quando couber, faça a chamada combinar com o momento (teste quebrado, escolha de nome,
revisão de código), sem trazer detalhe técnico: o detalhe fica na pergunta.

Tom: leve, simpático e educado, como um colega gente boa pedindo ajuda. Uma ou duas
frases curtas. Sem exagero, sem gíria pesada, sem palavrão, sem piada com a pessoa.
Em qualquer idioma, evite regionalismo forte e tratamento íntimo demais
(ex. em português: "Ô de casa!", "Oi, sumido!"). A chamada sempre
pede ajuda de forma clara, não só anuncia que há um problema: termine com o pedido,
de preferência em forma de pergunta ("Me ajuda?", "Can you help?", "¿Me ayudas?").

Sem sinal claro da variante do usuário, use a forma neutra, entendida em qualquer país:

- **Espanhol:** trate por "tú"; no plural use "ustedes" (nunca "vosotros" nem as formas
  dele, como "usáis", "tenéis"). Evite expressões que só existem num país; prefira
  "¿Me ayudas?" ou "¿Me das una mano?".
- **Inglês:** evite gíria britânica ou americana muito marcada.

Se o usuário der sinal da variante (usa "vosotros", "ordenador", "vale"; ou "computadora",
"ahorita"), siga a dele.

Escreva a chamada direto no idioma e na variante do usuário, com expressões naturais
dela. Não traduza nem adapte chamadas de outro idioma: "meu consagrado" vira
"my consecrated one" e perde a graça.

### Chamadas favoritas do usuário

O usuário guarda chamadas de que gosta num arquivo de favoritas, uma por linha, em
seções por idioma (`[pt-BR]`, `[pt-PT]`, `[en]`…). Para ver as do idioma da conversa:
`SKILL_DIR/popup.py favorite list --lang <código>`. Você pode usar uma favorita
exatamente como está, desde que seja da seção do idioma desta conversa. Nunca
traduza nem adapte favoritas de outra seção.

O script confere as regras e **recusa o pop-up com exit 7** quando:

- a chamada já foi usada nesta tarefa (favorita ou não);
- o pop-up anterior já usou uma favorita (nunca duas seguidas);
- a favorita é de outro idioma ou variante.

Com exit 7, a janela não abre e o motivo vai para stderr: escreva outra chamada e
rode o comando de novo.

Se o usuário pedir para guardar, tirar ou ver favoritas:

```bash
SKILL_DIR/popup.py favorite add --lang <código> "<chamada>"
SKILL_DIR/popup.py favorite rm  --lang <código> "<chamada>"
SKILL_DIR/popup.py favorite list [--lang <código>]
```

Na janela GTK, a ⭐ no canto guarda a chamada que está aparecendo; clicar de novo tira.

### Referência de tom em outros idiomas

Estes exemplos só mostram o jeito. **Não reutilize** estas frases, os vocativos nem
as imagens delas, nem com outras palavras: escreva sempre uma chamada nova, feita
para o momento.

- English: "Hey there, sorry to bug you, but I could use a hand with something. Got a sec?"
- Español: "Oye, perdona la molestia, ¿me echas una mano con una duda?"

Passe a chamada em `--greeting` nos comandos abaixo e use-a também no
`notify-send` de pergunta pendente.

## A janela

O script `SKILL_DIR/popup.py` mostra a chamada em destaque laranja, a pergunta e um
contador de tempo. Toca um som ao abrir. Esc fecha.

Saída: a resposta em stdout. Exit 0 = respondeu, 1 = fechou ou recusou, 5 = timeout,
6 = sem tela ou sem interface gráfica (faça a pergunta no terminal),
7 = chamada recusada (veja "Chamadas favoritas do usuário"): escreva outra e rode de novo.
Avisos de troca de interface vão para stderr; não são a resposta.

O comando fica bloqueado até o usuário responder. Se a sua ferramenta de shell tem
limite de tempo, use um limite maior que o `--timeout` do script (ex.: 500 s para
`--timeout 300`).

### Pergunta direta: cartões + resposta escrita

Cada `--option` é `"emoji|título|descrição"`. Escolha um emoji que combine com a opção e
escreva uma descrição curta do que acontece se ela for escolhida. O usuário clica no
cartão, aperta o número (1-9) ou escreve a própria resposta no campo embutido.

```bash
SKILL_DIR/popup.py ask --timeout 300 --lang <código do idioma da conversa> \
  --greeting "<chamada escrita agora para este pop-up>" \
  --question "<pergunta, com o contexto mínimo para decidir>" \
  --context "<opcional: uma linha de apoio, em cinza>" \
  --option "🧩|<opção 1>|<o que acontece>" \
  --option "🚀|<opção 2>|<o que acontece>"
echo "exit=$?"
```

### Sim ou não

```bash
SKILL_DIR/popup.py yesno --timeout 300 --lang <código do idioma da conversa> \
  --greeting "<chamada>" --question "<pergunta de sim ou não>"
echo "exit=$?"   # 0 = yes, 1 = no
```

### Chamada ao terminal

```bash
SKILL_DIR/popup.py terminal --timeout 300 --lang <código do idioma da conversa> \
  --greeting "<chamada>" \
  --question "<pedido, no idioma do usuário, para ele ir ao terminal>: <resumo de uma linha da dúvida>"
```

Depois disso, espere a resposta no terminal normalmente.

## Sem resposta

Exit diferente de 0 com resposta vazia (janela fechada, timeout ou exit 6): não decida
sozinho algo que só o usuário pode decidir. Deixe a pergunta escrita no terminal.
Em Linux com `notify-send`, avise também:

```bash
notify-send --urgency=critical --icon="SKILL_DIR/assets/mascote.svg" \
  "${POPUP_AGENT:-Agente}" "<chamada> Pergunta pendente no terminal."
```
