#!/bin/sh
# Compile locally with the existing Tectonic installation. No Overleaf account.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(dirname -- "$script_dir")
cd "$repo_dir/paper"
case "${1:-main}" in
  main|template) target=${1:-main} ;;
  *) echo "Usage: $0 [main|template]" >&2; exit 2 ;;
esac
tectonic_bin=${TECTONIC_BIN:-}
if [ -z "$tectonic_bin" ]; then
  tectonic_bin=$(command -v tectonic || true)
fi
if [ -z "$tectonic_bin" ]; then
  for candidate in /opt/homebrew/bin/tectonic /usr/local/bin/tectonic; do
    if [ -x "$candidate" ]; then tectonic_bin=$candidate; break; fi
  done
fi
if [ -z "$tectonic_bin" ]; then
  echo "Tectonic is required. Install it with: brew install tectonic" >&2
  exit 127
fi
mkdir -p build ../output/pdf
# Build in a temporary directory so a failed compile preserves the last good PDF.
build_dir=$(mktemp -d "build/.${target}.XXXXXX")
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM
if [ "${LATEX_OFFLINE:-0}" = 1 ]; then set -- --only-cached; else set --; fi
if "$tectonic_bin" "$@" --untrusted --synctex --keep-logs --outdir "$build_dir" "$target.tex"; then
  mv "$build_dir/$target.pdf" "../output/pdf/$target.pdf"
  if [ -f "$build_dir/$target.synctex.gz" ]; then
    mv "$build_dir/$target.synctex.gz" "../output/pdf/$target.synctex.gz"
  fi
  if [ -f "$build_dir/$target.log" ]; then mv "$build_dir/$target.log" "build/$target.log"; fi
  echo "Built: $repo_dir/output/pdf/$target.pdf"
else
  if [ -f "$build_dir/$target.log" ]; then mv "$build_dir/$target.log" "build/$target.log"; fi
  echo "Compile failed. See paper/build/$target.log. The last good PDF is preserved." >&2
  exit 1
fi
