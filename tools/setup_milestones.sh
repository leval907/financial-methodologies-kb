#!/usr/bin/env bash
set -euo pipefail

# === Настройки ===
: "${GH_REPO:?Set GH_REPO like 'owner/repo'}"

echo "Repo: $GH_REPO"

# Проверим, что gh установлен и авторизован
command -v gh >/dev/null 2>&1 || { echo "gh not found. Install GitHub CLI."; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh not authenticated. Run: gh auth login"; exit 1; }

echo "Setting up milestones and assigning issues..."

python3 - <<'PY'
import json, os, subprocess, sys, time

repo = os.environ["GH_REPO"]

# Определяем Milestones и соответствующие им задачи (по частичному совпадению заголовка)
milestones = {
    "Foundation (v0.1)": {
        "description": "Core architecture, glossary, templates, and standards.",
        "due_date": "2025-01-15", # Примерная дата
        "issues": [
            "Define core project terminology",
            "Create Glossary v1.0",
            "Add glossary validation script",
            "Define universal methodology template",
            "Enforce front matter standard",
            "Define contribution rules",
            "Define roadmap"
        ]
    },
    "Power of One (v0.2)": {
        "description": "Formalization of the Power of One methodology and tools.",
        "due_date": "2025-02-01",
        "issues": [
            "Formalize Power of One",
            "Separate Power of One modeling tool",
            "Define Power of One output report"
        ]
    },
    "Integration (v0.3)": {
        "description": "Integration with finance-knowledge, graph DB, and indexing.",
        "due_date": "2025-02-15",
        "issues": [
            "Define methodology indexing rules",
            "Define graph entities",
            "Add validation for methodology completeness",
            "Create Cross-Methodology Mapping"
        ]
    },
    "Methodologies Expansion (v0.4)": {
        "description": "Implementation of additional core methodologies (Simple Numbers, TOC, Lean Accounting).",
        "due_date": "2025-03-01",
        "issues": [
            "Formalize Simple Numbers Methodology",
            "Formalize Theory of Constraints",
            "Formalize Lean Accounting"
        ]
    }
}

def run_json(cmd):
    result = subprocess.check_output(cmd)
    return json.loads(result)

def run(cmd):
    subprocess.check_call(cmd)

# 1. Создаем Milestones
print("--- Creating Milestones ---")
existing_milestones = run_json(["gh", "api", f"repos/{repo}/milestones"])
existing_titles = {m["title"]: m["number"] for m in existing_milestones}

milestone_map = {} # title -> number

for title, data in milestones.items():
    if title in existing_titles:
        print(f"Milestone '{title}' already exists.")
        milestone_map[title] = existing_titles[title]
    else:
        print(f"Creating milestone '{title}'...")
        # gh api repos/:owner/:repo/milestones -f title="..." -f description="..."
        cmd = [
            "gh", "api", f"repos/{repo}/milestones",
            "-f", f"title={title}",
            "-f", f"description={data['description']}"
        ]
        # Можно добавить due_on, если нужно
        # "-f", f"due_on={data['due_date']}T00:00:00Z"
        
        res = run_json(cmd)
        milestone_map[title] = res["number"]

# 2. Получаем список всех issues
print("\n--- Fetching Issues ---")
# Получаем все открытые issues
all_issues = run_json(["gh", "issue", "list", "--repo", repo, "--state", "open", "--limit", "100", "--json", "number,title"])
print(f"Found {len(all_issues)} open issues.")

# 3. Привязываем issues к milestones
print("\n--- Assigning Issues to Milestones ---")
for m_title, m_number in milestone_map.items():
    target_issues = milestones[m_title]["issues"]
    
    for issue in all_issues:
        # Проверяем, подходит ли issue под один из паттернов этого майлстоуна
        for pattern in target_issues:
            if pattern.lower() in issue["title"].lower():
                print(f"Assigning issue #{issue['number']} '{issue['title']}' to '{m_title}'")
                run([
                    "gh", "issue", "edit", str(issue["number"]),
                    "--repo", repo,
                    "--milestone", m_title
                ])
                break # Переходим к следующему issue

print("\n✅ Milestones setup completed.")
PY
