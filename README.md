# Fonti

Install a font file or a whole folder of fonts on Windows from PowerShell. Fonti supports `.ttf`, `.otf`, `.ttc`, and `.otc` files.

## Quick start

With Git and [uv](https://docs.astral.sh/uv/getting-started/installation/) installed, run this in PowerShell. Fonti requires Python 3.13 or later.

```powershell
uv tool install --python 3.13 git+https://github.com/Noai-oss/fonti
```

If you have `CascadiaMono.ttf` in a local `fonts` folder, install it for your account and look it up.

```powershell
fonti install .\fonts\CascadiaMono.ttf
fonti list Cascadia
```

The two columns are the installed name and filename, separated by a tab.

```text
Cascadia Mono (TrueType)	CascadiaMono.ttf
```

## Installing fonts

Pass a directory to include its subdirectories, or give several files in one command.

```powershell
fonti install .\fonts
fonti install .\Regular.ttf .\Bold.ttf
```

Current-user installs require Windows 10 version 1809 or later. To install for everyone, open PowerShell as administrator and use `--system`.

```powershell
fonti install .\fonts --system
fonti list --system
```

You can rerun an install. Fonti skips identical, registered files and finishes registration if a previous run stopped after copying. Use `--replace` to overwrite a file with the same filename and different contents. If the font name already points to another file, use `list` to find the conflicting entry.

## Inspecting and removing fonts

Use `info` on a file or directory to see the name Fonti will register. Use `list` to find installed fonts by name or filename. Its optional keyword is a case-insensitive, literal substring.

```powershell
fonti info .\fonts\CascadiaMono.ttf
fonti list Mono
```

To uninstall a font, copy its exact filename or installed name from `list`. Quote names containing spaces.

```powershell
fonti remove 'CascadiaMono.ttf'
```

You can pass several targets. Fonti checks every target before removing any of them. If a filename is ambiguous, use the installed name. Files shared by other entries in the same scope and originals outside its font directory are preserved. To remove a system font, add `--system` in an elevated PowerShell window.

## Using Fonti in scripts

- `install` exits with code `0` when every input was installed or already present. A conflict, an input with no supported fonts, or a write failure stops the batch and returns a nonzero code. The error goes to stderr, and earlier successful installs remain in place.
- If Windows cannot activate a font immediately, Fonti reports a warning. The file and registration are in place, and a restart may be needed before apps can use it.
- `list` returns exit code `0` and prints nothing when its search has no matches.

## Development

Run the test suite from a checkout on Windows.

```powershell
uv sync --locked
uv run pytest
uv run fonti --help
```
