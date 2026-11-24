"""Interface WPF do pop-up, para o Windows nativo.

Monta um script do PowerShell 5.1 (que já vem no Windows) com uma janela WPF: os
controles são nativos, mas o desenho segue o da janela GTK. O script é gravado num
.ps1 temporário em UTF-8 com BOM e rodado com `powershell -File`: o comando codificado
passaria do limite de 32 KB, então `-EncodedCommand` não serve. O arquivo é apagado
por `popup.py`.

Emoji colorido vem do Emoji.Wpf, que depende de Stfu e de Typography. As DLLs ficam
em `assets/wpf/` (nenhuma instalação pelo usuário) e são carregadas nesta ordem:
Stfu, Typography.OpenFont, Typography.GlyphLayout, Emoji.Wpf.

Uso interno (por `popup.py`):
    wpf.script(a, wpf.PASTA, controle)
    wpf.aplicar_favorita(a, controle)

O tema segue o Windows (HKCU AppsUseLightTheme). Para depurar, o script aceita
`-Tema light` ou `-Tema dark`.
"""
import base64
import json
import os
import subprocess
import sys

import favoritas as fav
import textos as tx

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "assets", "wpf")
MODELO = os.path.join(AQUI, "wpf.ps1")
DLLS = ("Stfu.dll", "Typography.OpenFont.dll", "Typography.GlyphLayout.dll", "Emoji.Wpf.dll")


def completo():
    """As quatro DLLs vendorizadas estão na pasta? (não olha o PowerShell nem a tela)"""
    return os.path.isdir(PASTA) and all(os.path.isfile(os.path.join(PASTA, d)) for d in DLLS)


# ---------------------------------------------------------------- dados

def _titulo(t):
    try:
        br = subprocess.run(["git", "branch", "--show-current"], capture_output=True,
                            text=True, timeout=2).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        br = ""
    pasta = os.path.basename(os.getcwd())
    agente = tx.env("POPUP_AGENT", "POPUP_AGENTE") or t["agente"]
    return f"✨ {agente} · {pasta}" + (f" · {br}" if br else "")


def _contador(t):
    """Antes/depois de m:ss, sem o emoji (o texto do contador já tem o relógio)."""
    try:
        pre, pos = t["contador"].split("{m}:{s:02d}")
    except ValueError:
        return "", ""
    return pre.replace("⏳", "").lstrip(), pos


def _opcoes(a):
    saida = []
    for i, spec in enumerate(a.opcao, 1):
        emoji, titulo, desc = [p.strip() for p in (spec.split("|") + ["", ""])[:3]]
        if not titulo:
            emoji, titulo = "👉", emoji
        saida.append({"emoji": emoji or "👉", "titulo": titulo, "desc": desc,
                      "valor": titulo, "tecla": i})
    return saida


def _favorita(a):
    codigo = getattr(a, "idioma_fav", "") or getattr(a, "idioma", "")
    try:
        return fav.secao_de(a.chamada) in fav.secoes_validas(codigo)
    except OSError:
        return False


def dados(a, titulo=None, controle=None):
    """Tudo o que a janela precisa saber, pronto para virar JSON no script."""
    t = tx.textos(getattr(a, "idioma", "") or tx.PADRAO)
    pre, pos = _contador(t)
    return {
        "titulo": titulo or getattr(a, "titulo", None) or _titulo(t),
        "modo": a.modo,
        "chamada": a.chamada,
        "pergunta": a.pergunta,
        "contexto": getattr(a, "contexto", "") or "",
        "timeout": int(a.timeout),
        "sem_outra": bool(a.sem_outra),
        "t": dict(t),
        "cpre": pre,
        "cpos": pos,
        "opcoes": _opcoes(a) if a.modo == "pergunta" else [],
        "favorita": _favorita(a),
        "controle": controle or "",
    }


# ---------------------------------------------------------------- XAML

def _esc(t):
    """Texto para atributo XML, preservando quebras de linha."""
    t = str(t if t is not None else "").replace("\r\n", "\n").replace("\r", "\n")
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&apos;").replace("\n", "&#10;"))


def _cartao(o):
    desc = ""
    if o["desc"]:
        desc = f"""
              <emoji:TextBlock Text="{_esc(o['desc'])}" FontSize="12"
                               Foreground="__FG__" Opacity="0.65" TextWrapping="Wrap"
                               Margin="0,1,0,0"/>"""
    tecla = ""
    if o["tecla"] <= 9:
        tecla = f"""
            <Border Grid.Column="2" Width="22" Height="22" CornerRadius="4"
                    BorderBrush="__KEY_BORDER__" BorderThickness="1" VerticalAlignment="Center">
              <TextBlock Text="{o['tecla']}" FontFamily="Consolas" FontSize="11" FontWeight="Bold"
                         Foreground="__FG__" Opacity="0.55"
                         HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>"""
    return f"""
        <Border Style="{{StaticResource Cartao}}" Tag="{_esc(o['valor'])}">
          <Grid>
            <Grid.ColumnDefinitions>
              <ColumnDefinition Width="36"/>
              <ColumnDefinition Width="*"/>
              <ColumnDefinition Width="Auto"/>
            </Grid.ColumnDefinitions>
            <emoji:TextBlock Grid.Column="0" Text="{_esc(o['emoji'])}" FontSize="22"
                             HorizontalAlignment="Center" VerticalAlignment="Center"/>
            <StackPanel Grid.Column="1" Margin="2,0,8,0" VerticalAlignment="Center">
              <emoji:TextBlock Text="{_esc(o['titulo'])}" FontSize="15" FontWeight="Bold"
                               Foreground="__FG__" TextWrapping="Wrap"/>{desc}
            </StackPanel>{tecla}
          </Grid>
        </Border>"""


def _entrada(t):
    return f"""
      <Border Margin="0,10,0,0" CornerRadius="4" Background="__ENTRY_BG__" BorderBrush="__BORDER__" BorderThickness="1" Padding="10,6">
        <Grid>
          <Grid.ColumnDefinitions>
            <ColumnDefinition Width="*"/>
            <ColumnDefinition Width="Auto"/>
          </Grid.ColumnDefinitions>
          <Grid>
            <TextBox x:Name="entrada" Background="Transparent" BorderThickness="0" Padding="0"
                     Foreground="__FG__" CaretBrush="__ACCENT__" FontSize="14"
                     VerticalContentAlignment="Center" MinHeight="22"/>
            <TextBlock x:Name="dica" Text="{_esc(t['entrada'])}"
                       FontSize="14" Foreground="__FG__" Opacity="0.45"
                       IsHitTestVisible="False" VerticalAlignment="Center" Margin="2,0,0,0">
              <TextBlock.Style>
                <Style TargetType="TextBlock">
                  <Setter Property="Visibility" Value="Collapsed"/>
                  <Style.Triggers>
                    <DataTrigger Binding="{{Binding Text, ElementName=entrada}}" Value="">
                      <Setter Property="Visibility" Value="Visible"/>
                    </DataTrigger>
                  </Style.Triggers>
                </Style>
              </TextBlock.Style>
            </TextBlock>
          </Grid>
          <Button x:Name="aplicar" Grid.Column="1" Style="{{StaticResource BotaoIcone}}" Width="28" Height="28"
                  Content="&#xE70F;" FontSize="13" ToolTip="{_esc(t['responder'])}" VerticalAlignment="Center" Margin="8,0,0,0"/>
        </Grid>
      </Border>"""


def xaml(d):
    t = d["t"]
    selo = t[f"selo_{d['modo']}"]
    favorita = d["favorita"]
    estrela = "&#xE735;" if favorita else "&#xE734;"
    dica_fav = t["fav_salva"] if favorita else t["fav_salvar"]
    cards = "".join(_cartao(o) for o in d["opcoes"])
    entrada = _entrada(t) if d["modo"] == "pergunta" and not d["sem_outra"] else ""
    contexto = ""
    if d["contexto"]:
        contexto = f"""
          <emoji:TextBlock Text="{_esc(d['contexto'])}" FontSize="13" Foreground="__FG__"
                           Opacity="0.65" TextWrapping="Wrap" Margin="0,2,0,0"/>"""
    m, s = divmod(max(0, d["timeout"]), 60)
    contador = _esc(f"{d['cpre']}{m}:{s:02d}{d['cpos']}")
    if d["modo"] == "simnao":
        botoes = f"""
          <Button x:Name="naoBtn" Style="{{StaticResource BotaoSecundario}}" Content="{_esc(t['nao'])}" Margin="0,0,8,0"/>
          <Button x:Name="simBtn" Style="{{StaticResource BotaoPrimario}}" Content="{_esc(t['sim'])}"/>"""
    elif d["modo"] == "terminal":
        botoes = f"""
          <Button x:Name="jaVou" Style="{{StaticResource BotaoPrimario}}" Content="{_esc(t['ja_vou'])}"/>"""
    else:
        botoes = f"""
          <Button x:Name="agoraNao" Style="{{StaticResource BotaoSecundario}}" Content="{_esc(t['agora_nao'])}" Margin="0,0,8,0"/>"""
        if not d["sem_outra"]:
            botoes += f"""
          <Button x:Name="responder" Style="{{StaticResource BotaoPrimario}}" Content="{_esc(t['responder'])}"/>"""

    return f"""<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        xmlns:emoji="clr-namespace:Emoji.Wpf;assembly=Emoji.Wpf"
        Title="{_esc(d['titulo'])}"
        Width="632" SizeToContent="Height"
        WindowStyle="None" AllowsTransparency="True" Background="Transparent"
        ResizeMode="NoResize" WindowStartupLocation="CenterScreen"
        ShowInTaskbar="True" Topmost="True"
        FontFamily="Segoe UI" UseLayoutRounding="True"
        TextOptions.TextFormattingMode="Ideal">
  <Window.Resources>
    <Style x:Key="Cartao" TargetType="Border">
      <Setter Property="Background" Value="__CARD_BG__"/>
      <Setter Property="CornerRadius" Value="8"/>
      <Setter Property="Padding" Value="8,5"/>
      <Setter Property="Margin" Value="0,1"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Style.Triggers>
        <Trigger Property="IsMouseOver" Value="True">
          <Setter Property="Background" Value="__ACCENT_SOFT__"/>
        </Trigger>
      </Style.Triggers>
    </Style>
    <Style x:Key="BotaoPrimario" TargetType="Button">
      <Setter Property="Foreground" Value="White"/>
      <Setter Property="Background" Value="__ACCENT__"/>
      <Setter Property="FontSize" Value="14"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="Padding" Value="14,5"/>
      <Setter Property="MinHeight" Value="32"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="fundo" Background="{{TemplateBinding Background}}" CornerRadius="4" Padding="{{TemplateBinding Padding}}">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"
                                TextElement.Foreground="{{TemplateBinding Foreground}}"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="fundo" Property="Background" Value="__ACCENT_HOVER__"/>
              </Trigger>
              <Trigger Property="IsPressed" Value="True">
                <Setter TargetName="fundo" Property="Background" Value="__ACCENT_PRESS__"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="BotaoSecundario" TargetType="Button">
      <Setter Property="Foreground" Value="__FG__"/>
      <Setter Property="Background" Value="__BTN_BG__"/>
      <Setter Property="FontSize" Value="14"/>
      <Setter Property="Padding" Value="14,5"/>
      <Setter Property="MinHeight" Value="32"/>
      <Setter Property="BorderBrush" Value="__BORDER__"/>
      <Setter Property="BorderThickness" Value="1"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="fundo" Background="{{TemplateBinding Background}}"
                    BorderBrush="{{TemplateBinding BorderBrush}}" BorderThickness="{{TemplateBinding BorderThickness}}"
                    CornerRadius="4" Padding="{{TemplateBinding Padding}}">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"
                                TextElement.Foreground="{{TemplateBinding Foreground}}"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="fundo" Property="Background" Value="__BTN_HOVER__"/>
              </Trigger>
              <Trigger Property="IsPressed" Value="True">
                <Setter TargetName="fundo" Property="Background" Value="__BTN_PRESS__"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="BotaoIcone" TargetType="Button">
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="Foreground" Value="__ICON__"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="Width" Value="32"/>
      <Setter Property="Height" Value="32"/>
      <Setter Property="FontFamily" Value="Segoe Fluent Icons, Segoe MDL2 Assets"/>
      <Setter Property="FontSize" Value="14"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="fundo" Background="{{TemplateBinding Background}}" CornerRadius="4">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"
                                TextElement.Foreground="{{TemplateBinding Foreground}}"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="fundo" Property="Background" Value="__ICON_HOVER__"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="BotaoLegenda" TargetType="Button">
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="Foreground" Value="__FG__"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="Width" Value="46"/>
      <Setter Property="Height" Value="32"/>
      <Setter Property="FontFamily" Value="Segoe Fluent Icons, Segoe MDL2 Assets"/>
      <Setter Property="FontSize" Value="10"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="fundo" Background="{{TemplateBinding Background}}">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"
                                TextElement.Foreground="{{TemplateBinding Foreground}}"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="fundo" Property="Background" Value="__ICON_HOVER__"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
    <Style x:Key="BotaoFechar" TargetType="Button" BasedOn="{{StaticResource BotaoLegenda}}">
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="fundo" Background="{{TemplateBinding Background}}">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"
                                TextElement.Foreground="{{TemplateBinding Foreground}}"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="fundo" Property="Background" Value="#C42B1C"/>
                <Setter Property="Foreground" Value="White"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
  </Window.Resources>

  <Grid Margin="6">
    <Border CornerRadius="8" Background="__BG__">
      <Border.Effect>
        <DropShadowEffect BlurRadius="18" ShadowDepth="2" Opacity="__SHADOW__" Color="#000000"/>
      </Border.Effect>
    </Border>
    <Border CornerRadius="8">
      <Border.Background>
        <LinearGradientBrush StartPoint="0,0" EndPoint="0,1">
          <GradientStop Color="__GRAD1__" Offset="0"/>
          <GradientStop Color="__GRAD2__" Offset="0.46"/>
        </LinearGradientBrush>
      </Border.Background>
    </Border>

    <StackPanel Margin="28,0,28,22">
      <Grid x:Name="cabecalho" Height="40" Background="Transparent" Margin="0,0,-28,0">
        <Border HorizontalAlignment="Center" VerticalAlignment="Center" Background="__ACCENT_SOFT__" CornerRadius="4" Padding="8,2">
          <TextBlock Text="{_esc(selo)}" FontSize="11" FontWeight="Bold" Foreground="__ACCENT__"/>
        </Border>
        <StackPanel Orientation="Horizontal" HorizontalAlignment="Right" VerticalAlignment="Center">
          <Button x:Name="estrela" Style="{{StaticResource BotaoIcone}}" ToolTip="{_esc(dica_fav)}">
            <TextBlock x:Name="estrelaTexto" Text="{estrela}" FontFamily="Segoe Fluent Icons, Segoe MDL2 Assets" FontSize="14"/>
          </Button>
          <Button x:Name="minimizar" Style="{{StaticResource BotaoLegenda}}" Content="&#xE921;" ToolTip="Minimize"/>
          <Button x:Name="fechar" Style="{{StaticResource BotaoFechar}}" Content="&#xE8BB;" ToolTip="Close"/>
        </StackPanel>
      </Grid>

      <Grid Margin="0,4,0,0">
        <Grid.ColumnDefinitions>
          <ColumnDefinition Width="Auto"/>
          <ColumnDefinition Width="*"/>
        </Grid.ColumnDefinitions>
        <Viewbox Width="72" Height="72" VerticalAlignment="Top">
          <Canvas Width="128" Height="128">
            <Canvas.RenderTransform>
              <TranslateTransform x:Name="mascoteTransform"/>
            </Canvas.RenderTransform>
            <Canvas.Triggers>
              <EventTrigger RoutedEvent="Loaded">
                <BeginStoryboard>
                  <Storyboard>
                    <DoubleAnimation Storyboard.TargetName="mascoteTransform" Storyboard.TargetProperty="Y"
                                     From="0" To="-6" Duration="0:0:0.8"
                                     AutoReverse="True" RepeatBehavior="Forever">
                      <DoubleAnimation.EasingFunction>
                        <QuadraticEase EasingMode="EaseInOut"/>
                      </DoubleAnimation.EasingFunction>
                    </DoubleAnimation>
                  </Storyboard>
                </BeginStoryboard>
              </EventTrigger>
            </Canvas.Triggers>
            <Ellipse Width="108" Height="108" Canvas.Left="10" Canvas.Top="10">
              <Ellipse.Fill>
                <RadialGradientBrush GradientOrigin="0.4,0.3" Center="0.45,0.35" RadiusX="0.75" RadiusY="0.75">
                  <GradientStop Color="#F6B08F" Offset="0"/>
                  <GradientStop Color="#D97757" Offset="0.55"/>
                  <GradientStop Color="#B85A3C" Offset="1"/>
                </RadialGradientBrush>
              </Ellipse.Fill>
            </Ellipse>
            <Ellipse Width="18" Height="18" Fill="White" Canvas.Left="38" Canvas.Top="48"/>
            <Ellipse Width="18" Height="18" Fill="White" Canvas.Left="72" Canvas.Top="48"/>
            <Ellipse Width="8" Height="8" Fill="#4A2A20" Canvas.Left="45" Canvas.Top="54"/>
            <Ellipse Width="8" Height="8" Fill="#4A2A20" Canvas.Left="79" Canvas.Top="54"/>
            <Path Data="M 38,74 Q 64,94 90,74" Stroke="#7A3B2A" StrokeThickness="5"
                  StrokeStartLineCap="Round" StrokeEndLineCap="Round" Fill="Transparent"/>
            <TextBlock Text="?" Canvas.Left="92" Canvas.Top="8" FontSize="34" FontWeight="Bold"
                       Foreground="#FFF7F0" FontFamily="Segoe UI"/>
          </Canvas>
        </Viewbox>

        <StackPanel Grid.Column="1" Margin="14,2,0,0">
          <emoji:TextBlock Text="{_esc(d['chamada'])}" FontSize="24" FontWeight="ExtraBold"
                           Foreground="__ACCENT__" TextWrapping="Wrap"/>
          <emoji:TextBlock Text="{_esc(d['pergunta'])}" FontSize="17" Foreground="__FG__"
                           TextWrapping="Wrap" Margin="0,3,0,0"/>{contexto}
        </StackPanel>
      </Grid>

      <StackPanel x:Name="opcoes" Margin="0,16,0,0">{cards}
      </StackPanel>{entrada}

      <Grid Margin="0,14,0,0">
        <TextBlock x:Name="contador" Text="{contador}" FontSize="11" Foreground="__FG__"
                   Opacity="0.5" VerticalAlignment="Center"/>
        <StackPanel Orientation="Horizontal" HorizontalAlignment="Right">{botoes}
        </StackPanel>
      </Grid>
    </StackPanel>
  </Grid>
</Window>"""


# ---------------------------------------------------------------- script

def script(a, assets=None, controle=None):
    """Script .ps1 completo, com dados e XAML embutidos em base64."""
    assets = assets or PASTA
    d = dados(a, controle=controle)
    x = xaml(d)
    with open(MODELO, encoding="utf-8") as f:
        modelo = f.read()
    b64d = base64.b64encode(json.dumps(d, ensure_ascii=False).encode("utf-8")).decode("ascii")
    b64x = base64.b64encode(x.encode("utf-8")).decode("ascii")
    texto = (modelo.replace("__DADOS_B64__", b64d)
                   .replace("__XAML_B64__", b64x)
                   .replace("__ASSETS__", assets.replace("'", "''")))
    for marca in ("__DADOS_B64__", "__XAML_B64__", "__ASSETS__"):
        if marca in texto:
            raise ValueError(f"wpf.ps1: placeholder {marca} não substituído")
    return texto


def aplicar_favorita(a, caminho):
    """Lê o arquivo de controle da estrela (1/0) e atualiza as favoritas.

    Devolve True/False para o novo estado, ou None quando a estrela não foi clicada
    (arquivo ausente) ou não deu para gravar.
    """
    try:
        with open(caminho, encoding="utf-8") as f:
            valor = f.read().strip()
    except OSError:
        return None
    if valor not in ("0", "1"):
        return None
    try:
        if valor == "1":
            fav.adicionar(a.idioma_fav, a.chamada)
        else:
            fav.remover(a.idioma_fav, a.chamada)
    except (OSError, ValueError) as e:
        print(f"popup-wpf: could not save the favorite ({e})", file=sys.stderr)
        return None
    return valor == "1"
