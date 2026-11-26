# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project uses
[Semantic Versioning](https://semver.org/).

## [0.5.0] - 2026-11-26

### Added
- Presentation modes `window`, `dialog` and `notification` (`--mode` / `POPUP_MODE`),
  with a saved preference in `~/.config/popup/preferences.txt`.
- `popup.py preference` (`list`, `set MODE`) to read and change the saved mode.
- `popup.py notify` for completion notices, and notification-mode behavior for
  `terminal` (critical) and `ask`/`yesno` (exit 6 so the agent asks in the terminal).
- GTK `Gtk.Dialog` presentation, WPF notify mode, and WinForms/tkinter notify mode.
- `popup.py --version`; `doctor` shows the version.

### Changed
- `SKILL.md` and the READMEs now use `popup.py notify` instead of raw `notify-send`.
- Plugins regenerated for version 0.5.0.

## [0.4.1] - 2026-11-25

### Changed
- Favorite greetings are used by default, reducing repeated greetings.

## [0.4.0] - 2026-11-24

### Added
- WPF backend for native Windows windows.

## [0.3.3] - 2026-11-23

### Fixed
- Emoji rendering in the Windows window.

## [0.3.2] - 2026-11-23

### Fixed
- Low pop-up sound volume on Linux.

## [0.3.1] - 2026-11-23

### Changed
- No emoji in the Windows window (compatibility).

## [0.3.0] - 2026-11-23

### Added
- Experimental native Windows window on WSL (WinForms via PowerShell).

## [0.2.1] - 2026-11-23

### Changed
- README fixes and directory submission preparation.

## [0.2.0] - 2026-11-23

### Added
- English command-line interface, keeping the Portuguese aliases.

## [0.1.0] - 2026-11-23

### Added
- Initial release: GTK/zenity/kdialog/osascript/tkinter pop-ups, favorite greetings,
  and the `ask`, `yesno`, `terminal`, `doctor` and `favorite` commands.
