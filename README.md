# niri-ws-mode

Per-workspace **tiled / floating mode** for the [niri](https://github.com/YaLTeR/niri) Wayland compositor.

niri has no global "floating mode": floating is a second layer on every workspace. This tool adds one.
Mark a workspace as floating with a keybind and:

- every window on it goes floating, smaller than its tiled size and placed so windows cover each other as little as possible;
- every window you open there later is floated the same way;
- marking it as tiled again tiles everything and restores the widths the windows had before.

Other workspaces are not affected. Nothing is stored beyond a small state file in `$XDG_RUNTIME_DIR`, so it resets on reboot.

Tested on niri 26.04 with Dank Material Shell (DMS). It does not depend on DMS.

## Requirements

- niri with `move-window-to-floating`, `move-window-to-tiling` and `--id` on actions (tested on 26.04)
- Python 3.8+ (standard library only)
- `notify-send` (optional, for the "Workspace 3: floating" notification)

## Install

```sh
git clone <this repo> ~/Projects/niri-ws-mode
cd ~/Projects/niri-ws-mode
./install.sh
```

The script symlinks:

| Link | Target |
| --- | --- |
| `~/.local/bin/niri-ws-mode` | `bin/niri-ws-mode` |
| `~/.config/niri/niri-ws-mode.kdl` | `niri/niri-ws-mode.kdl` |

Then add one line to your niri config (for example `~/.config/niri/config.kdl`):

```kdl
include "niri-ws-mode.kdl"
```

Check the config with `niri validate`. The include adds:

- the keybind **`Mod+Ctrl+T`** to toggle the focused workspace;
- a `spawn-sh-at-startup` that runs the daemon.

To use another key, copy the `binds` block into your own binds file instead of including the snippet.
Start the daemon right away without logging out:

```sh
setsid niri-ws-mode daemon >/dev/null 2>&1 &
```

To remove everything: `./install.sh --uninstall`, delete the include line, and run `pkill -f 'niri-ws-mode daemon'`.

### Manual install without symlinks

Copy `bin/niri-ws-mode` anywhere, make it executable, and add to your niri config:

```kdl
binds {
    Mod+Ctrl+T { spawn-sh "/path/to/niri-ws-mode toggle"; }
}
spawn-sh-at-startup "/path/to/niri-ws-mode daemon"
```

## Usage

| Command | What it does |
| --- | --- |
| `niri-ws-mode toggle` | Flip the focused workspace between tiled and floating. |
| `niri-ws-mode daemon` | Watch niri's event stream and float new windows on floating workspaces. Only one instance runs. |
| `niri-ws-mode status` | Print `tiled` or `floating` for the focused workspace. Meant for status bars. |
| `niri-ws-mode float <json>` | Float one window given its niri JSON. Used internally by the daemon. |

## Configuration

Edit the constants at the top of `bin/niri-ws-mode`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `FLOAT_SCALE` | `0.8` | Floating size as a fraction of the tiled size. `0.5` is half, `0.67` is a third smaller. Also settable with the `NIRI_WS_MODE_SCALE` environment variable, which wins over the constant. |
| `EDGE_GAP` | `8` | Space kept free at the screen edge, in px. |
| `PLACE_STEP` | `20` | Resolution of the search for a free spot, in px. |
| `SETTLE_DELAY` | `0.3` | Seconds to wait before re-checking sizes of apps that resize themselves. |

Changes apply to the next toggle or new window without restarting the daemon.

## How it works

- **State** lives in `$XDG_RUNTIME_DIR/niri-ws-mode.json`: the mode per workspace id, plus the tiled size of every window that is currently floating because of this tool. A workspace with no entry is tiled.
- **Toggle to floating:** windows are taken in column order, floated, resized to `FLOAT_SCALE` of their tiled size, then placed. Their tiled size is saved first.
- **Toggle to tiled:** floating windows go back to the tiling layout, get their saved width back, and their height is reset to automatic. Windows that floated on their own (dialogs) are tiled too.
- **Placement:** niri exposes no working-area size, so the tool centers one window and reads where it lands to learn the real area (docks and bars included). It then searches a grid of positions for the one that overlaps the other floating windows least, preferring a slot that follows the old left-to-right order.
- **Daemon:** reads `niri msg --json event-stream`. When a window appears on, or moves to, a floating workspace, it starts a fresh `niri-ws-mode float` process. A fresh process means edits to the script apply immediately. It also forgets saved sizes of closed windows and drops state for workspaces that no longer exist.
- **Settling:** a short time after floating, the tool compares real window sizes with the targets. Apps that ignore or override the size get one retry and are re-placed using the size they actually have.

## Limitations

- A new window opens tiled for a moment before the daemon floats it. Window rules cannot match on workspace, so this can't be done in the niri config alone.
- Apps with a minimum size larger than the target stay bigger than `FLOAT_SCALE`.
- Tiling windows again puts them next to the active column one at a time, so their left-to-right order can reverse. Original positions are not remembered, only widths.
- Windows that float on their own (dialogs, `open-floating` rules) are tiled when you switch a workspace to tiled.
- Tiled windows inside a multi-window column lose their custom height when they return to tiling.

## Development

- `python3 tests/live-probe.py` is a smoke test against the running niri session. It opens four Alacritty windows, floats and tiles them, checks sizes and placement, and closes them.
- See [AGENTS.md](AGENTS.md) for notes on how the code is organised and what to watch out for.

## Ideas

- Bar indicator (a DMS widget or plugin calling `niri-ws-mode status`).
- Rewrite in a language that compiles to one binary (Rust or Go). The logic is small and the only I/O is `niri msg` and the state file.
