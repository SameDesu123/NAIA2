#!/bin/sh

set -eu

backend_root="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
python_executable="${backend_root}/../python/bin/python"

if [ ! -x "${python_executable}" ]; then
  echo "Bundled Python executable is missing: ${python_executable}" >&2
  exit 1
fi

exec "${python_executable}" -B "${backend_root}/NAIA_web_headless.py" "$@"
