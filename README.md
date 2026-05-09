# Fonti

A command-line tool for installing fonts on Windows.

- Use `fonttools` to extract the name from font file
- Configures ACL settings for user-level font directories
- Utilizes Windows GDI APIs and system broadcasts to ensure fonts are available immediately without a reboot

## Install

```powershell
uv tool install .
# or
uv tool install git+https://github.com/Noai-oss/fonti
```

## Commands

- `fonti install <source_dir> [--global]`
- `fonti list [--global]`
- `fonti uninstall "<font_name>" [--global]`

## Reference

- [WM_FONTCHANGE](https://learn.microsoft.com/en-us/windows/win32/gdi/wm-fontchange)
- [AddFontResourceW]https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-addfontresourcew
- [fonttools](https://github.com/fonttools/fonttools)
- [scoop-nerd-fonts](https://github.com/matthewjberger/scoop-nerd-fonts)
