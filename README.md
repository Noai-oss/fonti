# Fonti

Install a font file or a whole folder of fonts on Windows from PowerShell. Fonti supports `.ttf`, `.otf`, `.ttc`, and `.otc` files.

## Quick start

With [uv](https://docs.astral.sh/uv/getting-started/installation/) installed, run this in PowerShell to install Fonti from PyPI. Fonti requires Python 3.13 or later.

```powershell
uv tool install fonti
```

To install a single font for your Windows account, pass its path.

```powershell
fonti install .\Regular.ttf
```

## Install a font family from a release ZIP

Open PowerShell in an empty folder. Download the font archive from the [LXGW WenKai v1.530 release](https://github.com/lxgw/LxgwWenKai/releases/tag/v1.530) and extract it.

```powershell
$url = 'https://github.com/lxgw/LxgwWenKai/releases/download/v1.530/lxgw-wenkai-v1.530.zip'
Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile .\lxgw-wenkai-v1.530.zip -ErrorAction Stop
Expand-Archive -LiteralPath .\lxgw-wenkai-v1.530.zip -DestinationPath .\wenkai -ErrorAction Stop
```

Preview the fonts, install the extracted directory for your account, then list the installed entries. Fonti searches subdirectories recursively.

```powershell
fonti info .\wenkai
fonti install .\wenkai
fonti list WenKai
```

The archive includes Light, Regular, and Medium weights for both LXGW WenKai and LXGW WenKai Mono. Look for six matching rows. Each shows an installed name and a filename, separated by a tab. One of them is the Regular weight.

```text
LXGW WenKai (TrueType)	LXGWWenKai-Regular.ttf
```

**Optional cleanup.** To remove just the Regular font shown above, pass its exact filename. The other five fonts from the archive will still appear in the list.

```powershell
fonti remove 'LXGWWenKai-Regular.ttf'
fonti list WenKai
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

To uninstall a font, copy its exact filename or installed name from `list`. Quote names containing spaces. You can pass several targets. Fonti checks every target before removing any of them. If a filename is ambiguous, use the installed name. Files shared by other entries in the same scope and originals outside its font directory are preserved. To remove a system font, add `--system` in an elevated PowerShell window.

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
