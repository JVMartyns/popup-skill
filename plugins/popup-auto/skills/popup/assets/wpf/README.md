# WPF assets

Vendored DLLs for the native Windows window (`../wpf.py` + `../wpf.ps1`). The user
does not install anything: PowerShell 5.1 and .NET Framework 4.x already come with
Windows.

| File | Version | Source | License |
|---|---|---|---|
| `Emoji.Wpf.dll` | 0.3.4 | https://github.com/samhocevar/emoji.wpf | WTFPL v2 (`LICENSE-Emoji.Wpf.txt`) |
| `Stfu.dll` | 0.1.1 | https://github.com/samhocevar/stfu | WTFPL v2 (`LICENSE-Stfu.txt`) |
| `Typography.OpenFont.dll` | from Emoji.Wpf 0.3.4 | https://github.com/samhocevar-forks/typography | MIT (`LICENSE-Typography.md`) |
| `Typography.GlyphLayout.dll` | from Emoji.Wpf 0.3.4 | https://github.com/samhocevar-forks/typography | MIT (`LICENSE-Typography.md`) |

Load order matters: `Stfu.dll` first, then `Typography.OpenFont.dll`,
`Typography.GlyphLayout.dll`, and `Emoji.Wpf.dll` last. `wpf.ps1` does it in that
order; changing it makes `Emoji.Wpf` fail to load.

The files come from the NuGet packages:

```text
https://api.nuget.org/v3-flatcontainer/emoji.wpf/0.3.4/emoji.wpf.0.3.4.nupkg
https://api.nuget.org/v3-flatcontainer/stfu/0.1.1/stfu.0.1.1.nupkg
```

Only `lib/net40/*.dll` is used (PowerShell 5.1 runs on .NET Framework). Total size is
about 1.8 MB.
