#!/usr/bin/env bash
# Install guided-resume-studio into the local agent skills directory.
# Usage: install.sh [git-repo-url] [target-skills-dir]
set -euo pipefail

REPO_URL="${1:-https://github.com/<owner>/guided-resume-studio.git}"
SKILL_NAME="guided-resume-studio"

pick_skills_dir() {
  if [ -n "${2:-}" ]; then printf '%s' "$2"; return; fi
  for candidate in "${CODEX_HOME:-$HOME/.codex}/skills" "$HOME/.agents/skills" "$HOME/.kimi-code/skills" "$HOME/.claude/skills"; do
    if [ -d "$candidate" ]; then printf '%s' "$candidate"; return; fi
  done
  printf '%s' "${CODEX_HOME:-$HOME/.codex}/skills"
}

SKILLS_DIR="$(pick_skills_dir "$@")"
TARGET="$SKILLS_DIR/$SKILL_NAME"
mkdir -p "$SKILLS_DIR"

if [ -e "$TARGET" ]; then
  echo "error: $TARGET already exists; remove it or pass a different target dir" >&2
  exit 1
fi

if command -v git >/dev/null 2>&1; then
  git clone --depth 1 "$REPO_URL" "$TARGET"
else
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  archive_url="${REPO_URL%.git}/archive/refs/heads/main.tar.gz"
  curl -fsSL "$archive_url" -o "$tmp/skill.tar.gz"
  tar -xzf "$tmp/skill.tar.gz" -C "$tmp"
  mv "$tmp/$SKILL_NAME-main" "$TARGET"
fi

python3 "$TARGET/scripts/quick_validate.py" "$TARGET"
echo "installed: $TARGET"
echo "restart your agent client, then ask it to build a resume for one target job."
