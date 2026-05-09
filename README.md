# Fonti

A command-line tool for installing and uninstalling fonts on Windows.

- Supports `.ttf`, `.otf`, `.ttc`, and `.otc` font files.
- Uses `fonttools` to calculate Windows font registry names.
- Installs fonts for the current user by default.
- Can install or uninstall global fonts with `--global` when run as administrator, or with `--global --elevate` to request UAC elevation.
- Calls Windows GDI APIs and broadcasts `WM_FONTCHANGE` so fonts can become available immediately. If immediate activation fails, the persistent install remains and a reboot may be required.

## Install

```powershell
uv tool install .
# or
uv tool install git+https://github.com/Noai-oss/fonti
```

## Usage

Inspect the registry name that Fonti will use:

```powershell
fonti inspect <font-file-or-directory>
```

Install a font file or all supported fonts under a directory:

```powershell
fonti install <font-file-or-directory>
fonti install <font-file-or-directory> --force
fonti install <font-file-or-directory> --global
fonti install <font-file-or-directory> --global --elevate
```

List installed fonts:

```powershell
fonti list
fonti list --global
```

Uninstall by exact registry name:

```powershell
fonti uninstall "Cascadia Mono Bold (TrueType)"
fonti uninstall "Cascadia Mono Bold (TrueType)" --global
fonti uninstall "Cascadia Mono Bold (TrueType)" --global --elevate
```

Uninstall by installed file name or absolute path:

```powershell
fonti uninstall --file CascadiaMono-Bold.ttf
fonti uninstall --file "C:\Users\me\AppData\Local\Microsoft\Windows\Fonts\CascadiaMono-Bold.ttf"
```

## Notes

- User installs write font files to `%LOCALAPPDATA%\Microsoft\Windows\Fonts` and registry values to `HKCU\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts`.
- Global installs write font files to `%WINDIR%\Fonts` and registry values to `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts`.
- `--force` overwrites an existing font file with the same file name. Without `--force`, existing files are skipped.
- `--elevate` starts a new administrator process through UAC. It is only useful with `--global`, and the elevated window stays open until you press Enter.
- `--file` is often easier than uninstalling by registry name, especially for font collections or long generated names.

## Reference

- [WM_FONTCHANGE](https://learn.microsoft.com/en-us/windows/win32/gdi/wm-fontchange)
- [AddFontResourceW](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-addfontresourcew)
- [fonttools](https://github.com/fonttools/fonttools)
- [scoop-nerd-fonts](https://github.com/matthewjberger/scoop-nerd-fonts)
