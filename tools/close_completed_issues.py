#!/usr/bin/env python3
"""
Close completed GitHub issues and add comments
"""

import json
import re
import requests
import subprocess

def get_github_token():
    """Extract GitHub token from git remote URL"""
    result = subprocess.run(
        ['git', 'remote', 'get-url', 'origin'],
        capture_output=True,
        text=True,
        cwd='/home/leval907/financial-methodologies-kb/financial-methodologies-kb'
    )
    
    url = result.stdout.strip()
    match = re.search(r'ghp_([A-Za-z0-9_]+)@', url)
    if match:
        return f"ghp_{match.group(1)}"
    
    raise ValueError("GitHub token not found in remote URL")

GITHUB_TOKEN = get_github_token()
REPO_OWNER = "leval907"
REPO_NAME = "financial-methodologies-kb"
BASE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Issues to close with completion comments
COMPLETED_ISSUES = {
    1: {
        "comment": "✅ Completed\n\n**Done:**\n- Created `docs/glossary/` structure\n- Created `data/glossary/` for YAML files\n- Defined term addition rules\n- Glossary separated from methodologies\n\n**Files:**\n- docs/glossary/README.md\n- data/glossary/ (25 terms)"
    },
    2: {
        "comment": "✅ Completed\n\n**Done:**\n- Added 25 YAML files in `data/glossary/`\n- Created corresponding MD files in `docs/glossary/terms/`\n- Terms cover methodologies, models, finance, and system layer\n\n**Terms included:**\nmethodology, model, modeling_tool, indicator, lever, rule, decision, artifact, cash_flow, working_capital, profitability, liquidity, diagnostic, management_logic, report_form, planning_model, scenario, sustainable_growth, driver, and more."
    },
    3: {
        "comment": "✅ Completed\n\n**Done:**\n- Created `tools/validate_glossary.py`\n- Validates:\n  - Term existence\n  - Duplicates\n  - Orphaned terms\n  - Front matter correctness\n- Runs from repository root\n\n**Usage:**\n```bash\npython3 tools/validate_glossary.py\n```"
    },
    4: {
        "comment": "✅ Completed\n\n**Done:**\n- Created `templates/` folder with comprehensive templates\n- 10 template files created\n- Clear separation: management logic vs tools\n\n**Templates:**\n- README.md, model.md, workflow.md, decisions.md, pitfalls.md, examples.md\n- methodology.yaml, indicator.yaml, rule.yaml\n- TEMPLATE_GUIDE.md"
    },
    5: {
        "comment": "✅ Completed\n\n**Done:**\n- Mandatory front matter standard established\n- Fields: `methodology_id`, `doc_type`, `glossary_terms`\n- Documented in templates and guide\n\n**Example:**\n```yaml\n---\nmethodology_id: cash-flow-story\ntags: [cash-flow, working-capital, diagnostics]\nglossary_terms: [methodology, model, indicator, cash_flow]\n---\n```"
    },
    8: {
        "comment": "✅ Completed\n\n**Done:**\n- Created standard output form for Power of One\n- 4 diagnostic blocks defined\n- Balance equation included\n- Power of One table structure\n- Sustainable Growth calculation\n- Management focus areas\n\n**Location:** templates/report_form.md"
    }
}

def close_issue(issue_number: int, comment: str):
    """Close issue with comment"""
    
    # Add comment
    comment_response = requests.post(
        f"{BASE_URL}/issues/{issue_number}/comments",
        headers=HEADERS,
        json={"body": comment}
    )
    
    if comment_response.status_code != 201:
        print(f"❌ Failed to add comment to #{issue_number}: {comment_response.status_code}")
        return False
    
    # Close issue
    close_response = requests.patch(
        f"{BASE_URL}/issues/{issue_number}",
        headers=HEADERS,
        json={"state": "closed"}
    )
    
    if close_response.status_code == 200:
        print(f"✅ Closed issue #{issue_number}")
        return True
    else:
        print(f"❌ Failed to close issue #{issue_number}: {close_response.status_code}")
        return False

def main():
    """Main function"""
    
    print("="*60)
    print("Closing Completed Issues")
    print("="*60)
    print(f"Repository: {REPO_OWNER}/{REPO_NAME}\n")
    
    success_count = 0
    fail_count = 0
    
    for issue_number, data in COMPLETED_ISSUES.items():
        print(f"\nProcessing issue #{issue_number}...")
        
        if close_issue(issue_number, data["comment"]):
            success_count += 1
        else:
            fail_count += 1
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print(f"✅ Successfully closed: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
