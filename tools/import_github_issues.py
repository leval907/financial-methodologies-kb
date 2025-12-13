#!/usr/bin/env python3
"""
Import issues and milestones to GitHub using REST API
"""

import json
import re
import requests
import sys
from pathlib import Path

# Extract token from git remote URL
def get_github_token():
    """Extract GitHub token from git remote URL"""
    import subprocess
    result = subprocess.run(
        ['git', 'remote', 'get-url', 'origin'],
        capture_output=True,
        text=True,
        cwd='/home/leval907/financial-methodologies-kb/financial-methodologies-kb'
    )
    
    url = result.stdout.strip()
    # Format: https://ghp_TOKEN@github.com/user/repo.git
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

def create_milestone(title: str, description: str = "", state: str = "open") -> int:
    """Create or get milestone"""
    
    # Check if milestone exists
    response = requests.get(
        f"{BASE_URL}/milestones",
        headers=HEADERS,
        params={"state": "all"}
    )
    
    if response.status_code == 200:
        milestones = response.json()
        for milestone in milestones:
            if milestone['title'] == title:
                print(f"✓ Milestone already exists: {title} (#{milestone['number']})")
                return milestone['number']
    
    # Create new milestone
    response = requests.post(
        f"{BASE_URL}/milestones",
        headers=HEADERS,
        json={
            "title": title,
            "description": description,
            "state": state
        }
    )
    
    if response.status_code == 201:
        milestone = response.json()
        print(f"✅ Created milestone: {title} (#{milestone['number']})")
        return milestone['number']
    else:
        print(f"❌ Failed to create milestone: {response.status_code}")
        print(response.json())
        return None

def get_existing_issues():
    """Get list of existing issue titles to avoid duplicates"""
    response = requests.get(
        f"{BASE_URL}/issues",
        headers=HEADERS,
        params={"state": "all", "per_page": 100}
    )
    
    if response.status_code == 200:
        issues = response.json()
        return {issue['title']: issue['number'] for issue in issues}
    
    return {}

def create_issue(title: str, body: str, labels: list, milestone_number: int = None) -> int:
    """Create GitHub issue"""
    
    payload = {
        "title": title,
        "body": body,
        "labels": labels
    }
    
    if milestone_number:
        payload["milestone"] = milestone_number
    
    response = requests.post(
        f"{BASE_URL}/issues",
        headers=HEADERS,
        json=payload
    )
    
    if response.status_code == 201:
        issue = response.json()
        print(f"✅ Created issue #{issue['number']}: {title}")
        return issue['number']
    else:
        print(f"❌ Failed to create issue: {response.status_code}")
        print(response.json())
        return None

def import_issues_from_file(filepath: str):
    """Import issues from JSON file"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        issues = json.load(f)
    
    print(f"\n📋 Loading issues from: {filepath}")
    print(f"   Found {len(issues)} issues\n")
    
    # Get existing issues to avoid duplicates
    existing_issues = get_existing_issues()
    print(f"📊 Found {len(existing_issues)} existing issues in repository\n")
    
    # Group by milestone
    milestones_map = {}
    
    for issue in issues:
        milestone_title = issue.get('milestone')
        if milestone_title and milestone_title not in milestones_map:
            milestone_number = create_milestone(
                title=milestone_title,
                description=f"Milestone for {milestone_title}"
            )
            milestones_map[milestone_title] = milestone_number
    
    print("\n" + "="*60)
    print("Creating issues...")
    print("="*60 + "\n")
    
    # Create issues
    created_count = 0
    skipped_count = 0
    
    for issue in issues:
        title = issue['title']
        
        # Skip if already exists
        if title in existing_issues:
            print(f"⊘ Skipped (exists): {title} (#{existing_issues[title]})")
            skipped_count += 1
            continue
        
        body = issue['body']
        labels = issue['labels']
        milestone_title = issue.get('milestone')
        milestone_number = milestones_map.get(milestone_title)
        
        issue_number = create_issue(title, body, labels, milestone_number)
        if issue_number:
            created_count += 1
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print(f"✅ Created: {created_count} issues")
    print(f"⊘  Skipped: {skipped_count} issues (already exist)")
    print(f"📊 Total:   {len(issues)} issues processed")
    print("="*60 + "\n")

def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print("Usage: python3 import_github_issues.py <issues_file.json>")
        print("\nExample:")
        print("  python3 import_github_issues.py issues_agent_pipeline.json")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    
    print("="*60)
    print(f"GitHub Issues Importer")
    print("="*60)
    print(f"Repository: {REPO_OWNER}/{REPO_NAME}")
    print(f"File:       {filepath}")
    print("="*60 + "\n")
    
    try:
        import_issues_from_file(filepath)
        print("🎉 Import completed successfully!\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
