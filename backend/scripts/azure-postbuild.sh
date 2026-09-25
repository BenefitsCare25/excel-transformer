#!/usr/bin/env bash
set -euo pipefail

venv_python="antenv/bin/python"
if [[ ! -x "$venv_python" ]]; then
  echo "Azure build virtual environment was not found" >&2
  exit 1
fi

# RapidOCR depends on desktop OpenCV; Azure's runtime lacks its GUI libraries.
"$venv_python" -m pip uninstall -y opencv-python
"$venv_python" -m pip install --no-deps --force-reinstall 'opencv-python-headless>=4.10.0'
"$venv_python" -c 'import cv2; print("Headless OpenCV:", cv2.__version__)'
