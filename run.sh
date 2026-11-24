#!/usr/bin/env bash
# 大梦 · 一键启动
set -euo pipefail
cd "$(dirname "$0")"
exec python3 app.py "$@"
