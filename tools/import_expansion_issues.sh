#!/usr/bin/env bash
set -euo pipefail

# === Настройки ===
: "${GH_REPO:?Set GH_REPO like 'owner/repo'}"
: "${ISSUES_JSON:=issues_expansion.json}"

# Новые Labels
LABELS=(
  simple-numbers toc lean-accounting mapping
)

echo "Repo: $GH_REPO"
echo "Issues file: $ISSUES_JSON"

# Проверим, что gh установлен и авторизован
command -v gh >/dev/null 2>&1 || { echo "gh not found. Install GitHub CLI."; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh not authenticated. Run: gh auth login"; exit 1; }

# Создадим labels
echo "Creating labels (idempotent)..."
for l in "${LABELS[@]}"; do
  gh label create "$l" --repo "$GH_REPO" --force >/dev/null 2>&1 || true
done

# Импорт issues
echo "Creating issues..."
python3 - <<'PY'
import json, os, subprocess, shlex, sys

repo = os.environ["GH_REPO"]
path = os.environ.get("ISSUES_JSON", "issues_expansion.json")

with open(path, "r", encoding="utf-8") as f:
    issues = json.load(f)

def run(cmd):
    subprocess.check_call(cmd)

for i, item in enumerate(issues, 1):
    title = item["title"]
    body = item.get("body", "")
    labels = item.get("labels", [])
    cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
    for lab in labels:
        cmd += ["--label", lab]
    print(f"[{i}/{len(issues)}] {title}")
    run(cmd)

print("Done.")
PY

echo "✅ Expansion import completed."
