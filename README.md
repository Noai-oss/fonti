# Fonti

A Unix-philosophy inspired command-line tool for installing and managing fonts on Windows.

- **Stream-oriented**: Utilizes Python generators to lazily stream font metadata and paths, avoiding in-memory bottlenecks.
- **Fail-fast**: Pre-flight OS verification guarantees safe execution.
- **Pipeline-friendly**: Clean list output and explicit install/remove status lines, easily scriptable.
- Supports `.ttf`, `.otf`, `.ttc`, and `.otc` font files.
- Uses `fonttools` to analyze font metadata and calculate Windows font registry names.
- Can install or uninstall global fonts with `--global` when run as administrator.
- Calls Windows GDI APIs and broadcasts `WM_FONTCHANGE` so fonts can become available without rebooting when immediate activation succeeds.

## Install

```powershell
uv tool install .
# or
uv tool install git+https://github.com/Noai-oss/fonti
```

## Commands

Fonti provides a clean, 4-command CLI built with Typer:

- `info`: Show font metadata before installing.
- `install`: Install font files locally or globally.
- `ls`: List currently installed fonts.
- `rm`: Remove installed fonts by referencing names, exact files, or regex filters.

### info

Show the registry name that Fonti will use:

```powershell
fonti info <font-file-or-directory>
```

### install

Install a font file or all supported fonts under a directory:

```powershell
fonti install <font-file-or-directory>
fonti install <font-file-or-directory> --force
fonti install <font-file-or-directory> -g        # Install globally
fonti install <font-file-or-directory> --format ttf,otf
fonti install <font-file-or-directory> -e 'Mono|Code' # Regex filtering
```

### ls

List installed fonts, suitable for pipeline integration:

```powershell
fonti ls
fonti ls -g
fonti ls 'Mono|Code'
```

### rm

Uninstall by exact registry name:

```powershell
fonti rm "Cascadia Mono Bold (TrueType)"
fonti rm "Cascadia Mono Bold (TrueType)" -g
```

Uninstall by absolute path or direct filename matches:

```powershell
fonti rm CascadiaMono-Bold.ttf
fonti rm "C:\Users\me\AppData\Local\Microsoft\Windows\Fonts\CascadiaMono-Bold.ttf"
```

Uninstall using regex filters. Because this impacts multiple fonts, preview with `ls` first, then pass `--yes` (`-y`):

```powershell
fonti ls 'Mono|Code'
fonti rm -e 'Mono|Code' -y
```

## Architecture Notes

- **User Installs**: Writes fonts to `%LOCALAPPDATA%\Microsoft\Windows\Fonts` and registry configuration to `HKCU\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts`.
- **Global Installs**: Writes fonts to `%WINDIR%\Fonts` and registry configuration to `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts`.
- **Idempotency**: `--force` overwrites existing target files. Without it, existing files correctly short-circuit avoiding redundant IO.
- **Pipelining**: Designed following the Unix philosophy—modules like `scan.py`, `meta.py`, and `install.py` emit and consume generator streams to process pipelines uniformly.
- **Fail-safe Filtering**: Filtered uninstalls explicitly require a confirmation flag (`-y`) to maintain script safety.

## Development

Run tests without touching real font installs:

```powershell
uv run pytest
uv run pytest --cov=fonti --cov-report=term-missing
```

The test suite mocks Windows registry and GDI calls; it does not require manual font installation.

## References

- [WM_FONTCHANGE](https://learn.microsoft.com/en-us/windows/win32/gdi/wm-fontchange)
- [AddFontResourceW](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-addfontresourcew)
- [fonttools](https://github.com/fonttools/fonttools)
