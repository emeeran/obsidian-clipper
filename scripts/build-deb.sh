#!/usr/bin/env bash
#
# Build a single self-contained .deb for Obsidian Clipper.
#
# The bundle ships:
#   - the app and ALL Python dependencies, installed into a flat lib dir
#     (so no pip/uv resolve is needed at runtime), and
#   - a /usr/bin/obsidian-clipper wrapper.
#
# System capture tools (xclip, flameshot, tesseract-ocr, …) cannot be bundled
# as Python packages, so they are declared as Recommends and pulled by apt on
# install. The only hard runtime requirement is the system python3 (>= 3.10).
#
# Usage:
#   scripts/build-deb.sh            # builds dist/obsidian-clipper_<ver>_all.deb
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# --- metadata ---------------------------------------------------------------
VERSION="$(grep -E '^__version__' obsidian_clipper/_version.py | sed -E 's/.*"([^"]+)".*/\1/')"
MAINTAINER_NAME="$(git config user.name || echo 'Meeran E Mandhini')"
MAINTAINER_EMAIL="$(git config user.email || echo 'noreply@example.com')"
PKG="obsidian-clipper"
LIBDIR="/usr/share/${PKG}/lib"

if [[ -z "${VERSION}" ]]; then
  echo "ERROR: could not read version from obsidian_clipper/_version.py" >&2
  exit 1
fi

echo "▸ Building ${PKG} v${VERSION} (maintainer: ${MAINTAINER_NAME} <${MAINTAINER_EMAIL}>)"

# --- staging ----------------------------------------------------------------
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
LIB="$STAGE${LIBDIR}"
mkdir -p "$LIB" "$STAGE/DEBIAN" "$STAGE/usr/bin"

echo "▸ Installing app + Python deps (pinned from uv.lock) into flat lib dir…"
# Install the project's exact locked dependencies, then the project itself with
# --no-deps so resolution never drifts from the lock (reproducible builds).
uv export --frozen --no-dev --no-emit-project --quiet -o "$STAGE/reqs.txt"
uv pip install --target "$LIB" --quiet --no-cache-dir -r "$STAGE/reqs.txt" --no-deps .

# Pre-compile bytecode for faster cold-start from the keyboard shortcut.
python3 -m compileall -q "$LIB" || true

# Drop __pycache__ for test packages / stray caches to keep the bundle lean.
find "$LIB" -type d -name '__pycache__' -path '*/tests/*' -prune -exec rm -rf {} + 2>/dev/null || true

# --- wrapper ----------------------------------------------------------------
cat > "$STAGE/usr/bin/${PKG}" <<EOF
#!/bin/sh
# Bundled Obsidian Clipper launcher — execs the module against the bundled lib.
export PYTHONPATH="${LIBDIR}\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m obsidian_clipper "\$@"
EOF
chmod 0755 "$STAGE/usr/bin/${PKG}"

# --- installed-size + control ----------------------------------------------
INSTALLED_KB="$(du -sk "$STAGE/usr" | cut -f1)"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: ${PKG}
Version: ${VERSION}
Architecture: all
Maintainer: ${MAINTAINER_NAME} <${MAINTAINER_EMAIL}>
Installed-Size: ${INSTALLED_KB}
Depends: python3 (>= 3.10)
Recommends: xclip, tesseract-ocr, libnotify-bin, xdotool, flameshot
Suggests: wl-clipboard, grim, slurp, scrot, fzf | rofi
Section: utils
Priority: optional
Homepage: https://github.com/emeeran/obsidian-clipper
Description: Capture text, screenshots, and OCR to Obsidian (Local REST API)
 Linux CLI that captures highlighted text, screenshots (with OCR), and
 auto-detected citations (PDF/EPUB/browser) into an Obsidian vault via the
 Local REST API plugin. Bundled with its Python dependencies; system capture
 tools are installed as recommended dependencies.
EOF

# Normalize ownership so the deb isn't polluted with the builder's uid:gid.
if [[ "$(id -u)" -eq 0 ]]; then
  chown -R 0:0 "$STAGE"
else
  (command -v fakeroot >/dev/null && fakeroot chown -R 0:0 "$STAGE") || true
fi

# --- build ------------------------------------------------------------------
mkdir -p "$ROOT/dist"
DEB="$ROOT/dist/${PKG}_${VERSION}_all.deb"
rm -f "$DEB"

echo "▸ Packing deb…"
dpkg-deb --build --root-owner-group "$STAGE" "$DEB"

echo
echo "✔ Built: $DEB"
echo "  size: $(du -h "$DEB" | cut -f1)"
echo
echo "Install (auto-pulls recommended capture tools):"
echo "  sudo apt install ./$DEB"
echo "Or without recommends:"
echo "  sudo dpkg -i $DEB && sudo apt-get install -f"
echo
echo "Note: OCR uses tesseract-ocr (installed via Recommends). Non-English OCR"
echo "needs the matching language pack, e.g.:"
echo "  sudo apt install tesseract-ocr-deu   # German; set OBSIDIAN_OCR_LANGUAGE=deu"
echo "Note: --pick requires fzf or rofi (in Suggests; not auto-installed)."
