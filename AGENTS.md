# AGENTS.md

Notes for coding agents working on this repo. Read `README.md` first for what the tool does.

## Layout

```
bin/niri-ws-mode         The whole tool: one Python 3 file, standard library only.
niri/niri-ws-mode.kdl    Config snippet users include: keybind + daemon autostart.
install.sh               Symlinks the two files above into ~/.local/bin and ~/.config/niri.
tests/live-probe.py      Smoke test against the running niri session (opens real windows).
```

## Architecture (bin/niri-ws-mode)

- Talks to niri only through `niri msg` (`niri()`, `niri_json()`, `action()`). No sockets, no libraries.
- Commands: `toggle`, `daemon`, `status`, `float <window json>`.
- State file `$XDG_RUNTIME_DIR/niri-ws-mode.json`: `{"workspaces": {ws_id: "floating"|"tiled"}, "tiled": {window_id: [w, h]}}`. All writes go through `mutate_state()`, which holds a file lock and replaces the file atomically. Old flat-format files are still read.
- Key functions: `to_floating` / `to_tiling` (mode change and size save/restore), `arrange` (placement), `best_position` (min overlap search), `settle` (re-check sizes after `SETTLE_DELAY`).
- The daemon must stay a thin dispatcher. For each new window it spawns `niri-ws-mode float <json>` as a fresh process. Do not move sizing logic into the daemon process: it would keep old constants after the script is edited (this caused a real bug: toggled windows used `FLOAT_SCALE` 0.8 while new windows used the stale 0.6).
- Only the daemon loop itself (event handling) needs a restart after edits: `pkill -f '[n]iri-ws-mode daemon'`, then start it again.

## niri behaviour learned while building this

- Window rules can't match on workspace, so per-workspace "open floating" needs the daemon.
- `niri msg action ... --id N` works on any window, including non-focused ones.
- `move-floating-window -x N -y N` with plain numbers is absolute and relative to the output. It is not clamped to the screen; windows can be moved mostly off-screen.
- `center-window` centers in the real working area. Reading `tile_pos_in_workspace_view` and `tile_size` afterwards gives the area size (`2 * center`); on the author's setup the width is 1891, not 1920, because of a dock.
- `layout.tile_pos_in_workspace_view` is `null` for tiled windows. Floating windows have it, relative to their output.
- The first `WindowOpenedOrChanged` event for a window carries its final tiled size for the apps tested (Alacritty, Nautilus, Thunar, pavucontrol).
- A window moved to floating keeps its tiled size unless you set it, so `to_floating` always sets width and height explicitly.
- Binds and `spawn-at-startup` in included KDL files are merged by niri. `spawn` does not expand `~`; `spawn-sh` does.

## Working on it

- Check syntax: `python3 -m py_compile bin/niri-ws-mode` and `bash -n install.sh`.
- Check the snippet: put it next to a config containing only `include "niri-ws-mode.kdl"` and run `niri validate -c <that config>`.
- Run `python3 tests/live-probe.py` to test for real. It needs a niri session and Alacritty, and it flashes four windows on the focused workspace. It only touches windows whose title starts with `wsmode-probe`.
- To exercise functions from a one-off script, load the file with `importlib.machinery.SourceFileLoader` (see `tests/live-probe.py`); it has no `.py` extension.

## Cautions

- This runs against the user's live session. Never call `toggle` or mark workspaces during tests: it rearranges the user's real windows. Spawn throwaway windows and act on those ids only.
- Don't kill the daemon with `pkill -f "niri-ws-mode daemon"` from a shell command that contains that text: the pattern matches the shell itself. Use `pkill -f '[n]iri-ws-mode daemon'` in a separate command.
- Close every window you open for testing, and leave the state file as you found it.
- The user may have the script open in an editor and may edit constants such as `FLOAT_SCALE`. Don't reset them.
- Keep it dependency-free and keep comments sparse, in line with the existing code.

## Style

- Python, 4-space indent, standard library only, short functions, comments only for non-obvious behaviour.
- Defaults live in the constants block at the top of `bin/niri-ws-mode`. Document any new one in the README table.
- A user-visible change goes in the README; a change to how it is built or tested goes here.

## Roadmap

- Bar indicator via `niri-ws-mode status` (DMS plugin/widget).
- Possible rewrite in Rust or Go for a single compiled binary. Keep the CLI (`toggle`, `daemon`, `status`, `float`), the state file format and the placement behaviour so the config snippet doesn't change.
