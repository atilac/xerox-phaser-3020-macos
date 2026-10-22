#!/bin/bash
# Removes the Xerox Phaser 3020 USB queue, filter and PPD.
# SPDX-License-Identifier: MIT
set -uo pipefail

QUEUE="${QUEUE:-Xerox_Phaser_3020_USB}"
DEST="/Library/Printers/Xerox/P3020"
PPD="/Library/Printers/PPDs/Contents/Resources/Xerox_Phaser_3020_USB.ppd"

[ "$(id -u)" -eq 0 ] || { echo "run with sudo: sudo $0" >&2; exit 1; }

lpadmin -x "$QUEUE" 2>/dev/null && echo "removed queue $QUEUE" || echo "queue $QUEUE not present"
rm -f "$DEST/urftopjl" && echo "removed filter"
rmdir "$DEST" 2>/dev/null || true
rmdir "$(dirname "$DEST")" 2>/dev/null || true
rm -f "$PPD" && echo "removed PPD"
echo "Done."
