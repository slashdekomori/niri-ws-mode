#!/usr/bin/env bash
# Install niri-ws-mode by symlinking it into place, so edits in this repo apply
# immediately. Run with --uninstall to remove the links.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bin_link="${HOME}/.local/bin/niri-ws-mode"
kdl_link="${XDG_CONFIG_HOME:-$HOME/.config}/niri/niri-ws-mode.kdl"

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "$bin_link" "$kdl_link"
    echo "Removed $bin_link and $kdl_link"
    echo "Remove the include line from your niri config and stop the daemon:"
    echo "  pkill -f 'niri-ws-mode daemon'"
    exit 0
fi

for dep in niri python3; do
    command -v "$dep" >/dev/null || { echo "missing dependency: $dep" >&2; exit 1; }
done
command -v notify-send >/dev/null || echo "note: notify-send not found, mode notifications are disabled"

mkdir -p "$(dirname "$bin_link")" "$(dirname "$kdl_link")"
ln -sfn "$repo/bin/niri-ws-mode" "$bin_link"
ln -sfn "$repo/niri/niri-ws-mode.kdl" "$kdl_link"
echo "Linked $bin_link"
echo "Linked $kdl_link"

case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo "note: ~/.local/bin is not in PATH (the niri config uses the full path, so this is fine)" ;;
esac

cat <<EOF

Next steps:
  1. Add this line to your niri config (e.g. ~/.config/niri/config.kdl):

         include "niri-ws-mode.kdl"

  2. Check it:        niri validate
  3. Apply it:        niri reloads the config on save; the daemon starts on next login.
                      To start it now:  setsid niri-ws-mode daemon >/dev/null 2>&1 &
EOF
