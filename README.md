# Fonti

Install fonts on Windows from PowerShell. Fonti supports TrueType and OpenType files and collections (`.ttf`, `.otf`, `.ttc`, `.otc`).

```powershell
uv tool install git+https://github.com/Noai-oss/fonti
fonti install .\fonts
```

## Commands

```powershell
fonti install .\Regular.ttf .\Bold.ttf
fonti install .\fonts --system
fonti list 'Cascadia'
fonti remove 'CascadiaMono-Bold.ttf'
fonti info .\Regular.ttf
```

- **install** accepts one or more paths and searches directories recursively. Use `--replace` to allow overwriting a file with different contents at the same filename.
- **list** writes one installed name and filename per line, separated by a tab. Its optional keyword is a case-insensitive, literal substring of either field. An empty result is successful.
- **remove** takes one or more exact installed names or filenames from `list`. Quote names that contain spaces. All targets are resolved before removal. If a filename matches several entries, use the exact installed name. Files shared by other entries in the selected scope are kept. For fonts registered from outside that scope’s font directory, Fonti removes the registration and leaves the original file in place.
- **info** prints the registry name and font kind for a file or directory.

Commands operate on the current user's fonts by default. Add `--system` to install, list or remove system fonts. System installs and removals require an elevated shell. User installs require Windows 10 version 1809 or later.

Repeated installs skip identical, correctly registered files. If registration failed after copying, run the same command to finish installation. A filename conflict requires `--replace`; if the installed name belongs to another file, resolve the conflict with `list` and `remove` first.

Install exits with status 0 when all inputs are installed or already present. An input containing no supported fonts, a conflict, or a persistent installation failure returns a nonzero status and an error on stderr. A batch stops at the first error; completed fonts remain installed. Immediate activation is best effort: if Windows declines it, the persistent install still succeeds and Fonti prints a warning.

## Development

```powershell
uv sync --locked
uv run pytest
uv run fonti --help
```
