#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/guided-resume-studio"
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
TARGET_DIR="$CODEX_ROOT/skills/guided-resume-studio"

if [[ ! -f "$SOURCE_DIR/SKILL.md" ]]; then
  echo "error: skill source is missing: $SOURCE_DIR/SKILL.md" >&2
  exit 2
fi

if [[ -e "$TARGET_DIR" ]]; then
  echo "error: target already exists; installation stopped without overwriting: $TARGET_DIR" >&2
  exit 3
fi

mkdir -p "$CODEX_ROOT/skills"
cp -R "$SOURCE_DIR" "$TARGET_DIR"

echo "Installed guided-resume-studio to $TARGET_DIR"
echo 'Start a new Codex task and invoke: $guided-resume-studio'

