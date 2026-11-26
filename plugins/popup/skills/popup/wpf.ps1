param([ValidateSet('auto', 'light', 'dark')][string]$Tema = 'auto')
trap { [Console]::Error.WriteLine("popup-wpf: " + $_.ToString()); exit 3 }
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$d = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__DADOS_B64__')) | ConvertFrom-Json
$pasta = '__ASSETS__'

# WPF e as DLLs vendorizadas (nada para instalar). A Stfu precisa vir antes da
# Emoji.Wpf; Typography é dependência das duas.
Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
Add-Type -Path (Join-Path $pasta 'Stfu.dll')
Add-Type -Path (Join-Path $pasta 'Typography.OpenFont.dll')
Add-Type -Path (Join-Path $pasta 'Typography.GlyphLayout.dll')
Add-Type -Path (Join-Path $pasta 'Emoji.Wpf.dll')

$xamlTexto = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__XAML_B64__'))

# Tema: segue o Windows por padrão (AppsUseLightTheme); -Tema força para testar.
$escuro = $true
if ($Tema -eq 'light') {
    $escuro = $false
} elseif ($Tema -eq 'dark') {
    $escuro = $true
} else {
    $valor = 1
    try {
        $valor = (Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' -Name AppsUseLightTheme -ErrorAction Stop).AppsUseLightTheme
    } catch { }
    $escuro = ($valor -eq 0)
}

if ($escuro) {
    $paleta = @{
        BG = '#242424'; FG = '#F2F2F2'; ICON = '#E6E6E6'; ICON_HOVER = '#1AFFFFFF'
        CARD_BG = '#12FFFFFF'; ACCENT_SOFT = '#26D97757'; ACCENT = '#D97757'
        ACCENT_HOVER = '#C9623F'; ACCENT_PRESS = '#B85737'
        BTN_BG = '#2D2D2D'; BTN_HOVER = '#333333'; BTN_PRESS = '#3A3A3A'
        BORDER = '#3A3A3A'; ENTRY_BG = '#1F1F1F'; KEY_BORDER = '#33FFFFFF'
        GRAD1 = '#3DD97757'; GRAD2 = '#00D97757'; SHADOW = '0.35'
    }
} else {
    $paleta = @{
        BG = '#FAFAFA'; FG = '#1F1F1F'; ICON = '#4A4A4A'; ICON_HOVER = '#14000000'
        CARD_BG = '#0A000000'; ACCENT_SOFT = '#1FD97757'; ACCENT = '#C9623F'
        ACCENT_HOVER = '#B85737'; ACCENT_PRESS = '#A84A2E'
        BTN_BG = '#F3F3F3'; BTN_HOVER = '#E8E8E8'; BTN_PRESS = '#DEDEDE'
        BORDER = '#D6D6D6'; ENTRY_BG = '#FFFFFF'; KEY_BORDER = '#26000000'
        GRAD1 = '#2ED97757'; GRAD2 = '#00D97757'; SHADOW = '0.16'
    }
}
foreach ($chave in $paleta.Keys) {
    $xamlTexto = $xamlTexto.Replace("__${chave}__", $paleta[$chave])
}
foreach ($chave in $paleta.Keys) {
    if ($xamlTexto.Contains("__${chave}__")) { throw "theme token not replaced: __${chave}__" }
}

[xml]$xaml = $xamlTexto
$reader = New-Object System.Xml.XmlNodeReader $xaml
$win = [Windows.Markup.XamlReader]::Load($reader)

$script:resposta = $null
$script:cod = 1
$script:rest = [int]$d.timeout
$script:fav = [bool]$d.favorita

function AtualizaContador {
    $m = [math]::Floor($script:rest / 60)
    $s = $script:rest % 60
    $script:contador.Text = [string]$d.cpre + ('{0}:{1:00}' -f $m, $s) + [string]$d.cpos
}

function EnviarTexto {
    $caixa = $win.FindName('entrada')
    if ($null -eq $caixa) { return }
    $texto = $caixa.Text.Trim()
    if ($texto) {
        $script:resposta = $texto
        $script:cod = 0
        $win.Close()
    }
}

$win.Add_KeyDown({
    param($s, $e)
    if ($e.Key -eq [Windows.Input.Key]::Escape) {
        $script:resposta = $null; $script:cod = if ($d.modo -eq 'notify') { 0 } else { 1 }; $win.Close(); return
    }
    $caixa = $win.FindName('entrada')
    if ($caixa -and $caixa.IsKeyboardFocusWithin) {
        if ($e.Key -eq [Windows.Input.Key]::Enter) { EnviarTexto }
        return
    }
    if ($e.Key -eq [Windows.Input.Key]::Enter) {
        if ($d.modo -eq 'simnao') {
            $script:resposta = 'yes'; $script:cod = 0; $win.Close(); return
        }
        if ($d.modo -in @('terminal', 'notify')) {
            $script:resposta = 'ok'; $script:cod = 0; $win.Close(); return
        }
    }
    if ($caixa -and $caixa.Text) { return }
    $nome = $e.Key.ToString()
    if ($nome -match '^(D|NumPad)([1-9])$') {
        $n = [int]$Matches[2]
        $ops = @($d.opcoes)
        if ($n -le $ops.Count) {
            $script:resposta = [string]$ops[$n - 1].valor
            $script:cod = 0
            $win.Close()
        }
    }
})

$caixa = $win.FindName('entrada')
if ($caixa) {
    $caixa.Add_KeyDown({
        param($s, $e)
        if ($e.Key -eq [Windows.Input.Key]::Enter) {
            EnviarTexto
            $e.Handled = $true
        }
    })
}

$win.FindName('cabecalho').Add_MouseLeftButtonDown({
    param($s, $e)
    $src = $e.OriginalSource
    while ($src -and $src -ne $win) {
        if ($src -is [Windows.Controls.Button]) { return }
        $src = [Windows.Media.VisualTreeHelper]::GetParent($src)
    }
    $win.DragMove()
})

$botao = $win.FindName('minimizar')
if ($botao) { $botao.Add_Click({ $win.WindowState = [Windows.WindowState]::Minimized }) }
$botao = $win.FindName('fechar')
if ($botao) { $botao.Add_Click({ $script:resposta = $null; $script:cod = if ($d.modo -eq 'notify') { 0 } else { 1 }; $win.Close() }) }
$botao = $win.FindName('aplicar')
if ($botao) { $botao.Add_Click({ EnviarTexto }) }
$botao = $win.FindName('responder')
if ($botao) { $botao.Add_Click({ EnviarTexto }) }
$botao = $win.FindName('agoraNao')
if ($botao) { $botao.Add_Click({ $script:resposta = $null; $script:cod = 1; $win.Close() }) }
$botao = $win.FindName('naoBtn')
if ($botao) { $botao.Add_Click({ $script:resposta = 'no'; $script:cod = 1; $win.Close() }) }
$botao = $win.FindName('simBtn')
if ($botao) { $botao.Add_Click({ $script:resposta = 'yes'; $script:cod = 0; $win.Close() }) }
$botao = $win.FindName('jaVou')
if ($botao) { $botao.Add_Click({ $script:resposta = 'ok'; $script:cod = 0; $win.Close() }) }
$botao = $win.FindName('okBtn')
if ($botao) { $botao.Add_Click({ $script:resposta = 'ok'; $script:cod = 0; $win.Close() }) }

$painel = $win.FindName('opcoes')
foreach ($cartao in @($painel.Children)) {
    if ($cartao -is [Windows.Controls.Border]) {
        $cartao.Add_MouseLeftButtonDown({
            param($s, $e)
            if ($s.Tag) {
                $script:resposta = [string]$s.Tag
                $script:cod = 0
                $win.Close()
            }
        })
    }
}

$estrela = $win.FindName('estrela')
if ($estrela) {
    $estrela.Add_Click({
        $script:fav = -not $script:fav
        $texto = $win.FindName('estrelaTexto')
        if ($script:fav) {
            $texto.Text = [string][char]0xE735
            $win.FindName('estrela').ToolTip = $d.t.fav_salva
        } else {
            $texto.Text = [string][char]0xE734
            $win.FindName('estrela').ToolTip = $d.t.fav_salvar
        }
        if ($d.controle) {
            $valor = if ($script:fav) { '1' } else { '0' }
            [IO.File]::WriteAllText([string]$d.controle, $valor)
        }
    })
}

$script:contador = $win.FindName('contador')
if ($script:rest -le 0) { exit 5 }
AtualizaContador
$timer = New-Object Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromSeconds(1)
$timer.Add_Tick({
    $script:rest--
    if ($script:rest -le 0) {
        $script:resposta = $null; $script:cod = if ($d.modo -eq 'notify') { 0 } else { 5 }; $win.Close()
    } else {
        AtualizaContador
    }
})
$timer.Start()

$win.Add_Loaded({
    $win.Activate()
    try { [System.Media.SystemSounds]::Asterisk.Play() } catch { }
})

[void]$win.ShowDialog()
$timer.Stop()
if ($script:resposta) { [Console]::Out.Write([string]$script:resposta) }
exit [int]$script:cod
