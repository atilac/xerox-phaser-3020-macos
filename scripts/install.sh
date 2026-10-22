#!/bin/bash
#
# Xerox Phaser 3020 - USB printing on macOS 27+ (Apple Silicon)
# Installs the urftopjl CUPS filter, the PPD, and creates the print queue.
#
# SPDX-License-Identifier: MIT
set -euo pipefail

DEST="/Library/Printers/Xerox/P3020"
PPD_DIR="/Library/Printers/PPDs/Contents/Resources"
PPD_NAME="Xerox_Phaser_3020_USB.ppd"
QUEUE="${QUEUE:-Xerox_Phaser_3020_USB}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die() { echo "error: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run with sudo: sudo $0"

echo "==> Building urftopjl (universal arm64 + x86_64)"
command -v clang >/dev/null || die "clang not found - install Xcode Command Line Tools"
clang -O2 -Wall -Wextra -arch arm64 -arch x86_64 \
      -o "$REPO/src/urftopjl" "$REPO/src/urftopjl.c"
codesign -s - -f "$REPO/src/urftopjl" >/dev/null 2>&1 || true

echo "==> Installing filter to $DEST"
install -d -o root -g wheel -m 755 "$DEST"
install -o root -g wheel -m 755 "$REPO/src/urftopjl" "$DEST/urftopjl"

echo "==> Installing PPD"
install -d -o root -g wheel -m 755 "$PPD_DIR"
install -o root -g wheel -m 644 "$REPO/ppd/$PPD_NAME" "$PPD_DIR/$PPD_NAME"

echo "==> Locating printer on USB"
DEVICE_URI="$(/usr/libexec/cups/backend/usb 2>/dev/null \
  | awk '/Phaser 3020/ {print $2; exit}')"
[ -n "${DEVICE_URI:-}" ] || die "printer not found on USB - is it powered on and connected?"
echo "    $DEVICE_URI"

echo "==> Creating queue '$QUEUE'"
lpadmin -x "$QUEUE" 2>/dev/null || true
lpadmin -p "$QUEUE" -E -v "$DEVICE_URI" \
        -P "$PPD_DIR/$PPD_NAME" \
        -D "Xerox Phaser 3020 (USB)" \
        -L "USB" \
        -o printer-is-shared=false

echo
echo "Done. Queue '$QUEUE' is ready."
echo "Test with:  lp -d $QUEUE /path/to/file.pdf"
