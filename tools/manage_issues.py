#!/usr/bin/env python3
"""
GitHub Issues Management Tool
Helps track and manage project issues
"""

import json
import re
import requests
import subprocess
import sys
from typing import List, Dict

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

def get_issues(state="all", milestone=None, labels=None) -> List[Dict]:
    """Get issues from repository"""
    params = {"state": state, "per_page": 100}
    
    if milestone:
        # Get milestone number
        milestones = requests.get(f"{BASE_URL}/milestones", headers=HEADERS).json()
        milestone_num = next((m['number'] for m in milestones if m['title'] == milestone), None)
        if milestone_num:
            params['milestone'] = milestone_num
    
    if labels:
        params['labels'] = ','.join(labels)
    
    response = requests.get(f"{BASE_URL}/issues", headers=HEADERS, params=params)
    return response.json() if response.status_code == 200 else []

def print_issues_table(issues: List[Dict], show_milestone=True):
    """Print issues in a formatted table"""
    if not issues:
        print("No issues found.")
        return
    
    print(f"\n{'#':<5} {'State':<8} {'Title':<50} {'Labels':<30} {'Milestone':<20}")
    print("="*120)
    
    for issue in issues:
        number = f"#{issue['number']}"
        state = issue['state']
        title = issue['title'][:47] + "..." if len(issue['title']) > 50 else issue['title']
        labels = ", ".join([l['name'] for l in issue['labels']])[:27] + "..." if issue['labels'] else ""
        milestone = issue['milestone']['title'][:17] + "..." if issue['milestone'] else ""
        
        # Color coding
        state_symbol = "✅" if state == "closed" else "🔴"
        
        print(f"{number:<5} {state_symbol} {state:<6} {title:<50} {labels:<30} {milestone:<20}")

def list_by_milestone():
    """List issues grouped by milestone"""
    print("\n" + "="*60)
    print("Issues by Milestone")
    print("="*60)
    
    milestones_response = requests.get(f"{BASE_URL}/milestones", headers=HEADERS, params={"state": "all"})
    milestones = milestones_response.json() if milestones_response.status_code == 200 else []
    
    for milestone in milestones:
        print(f"\n📌 {milestone['title']} ({milestone['open_issues']} open / {milestone['closed_issues']} closed)")
        print("-" * 60)
        
        issues = get_issues(state="all", milestone=milestone['title'])
        
        for issue in issues:
            state_symbol = "✅" if issue['state'] == "closed" else "🔴"
            print(f"  {state_symbol} #{issue['number']}: {issue['title']}")

def list_open_issues():
    """List all open issues"""
    print("\n" + "="*60)
    print("Open Issues")
    print("="*60)
    
    issues = get_issues(state="open")
    print_issues_table(issues)
    
    print(f"\nTotal open issues: {len(issues)}")

def list_closed_issues():
    """List recently closed issues"""
    print("\n" + "="*60)
    print("Recently Closed Issues")
    print("="*60)
    
    issues = get_issues(state="closed")[:10]  # Last 10 closed
    print_issues_table(issues)

def next_tasks(limit=5):
    """Show next tasks to work on"""
    print("\n" + "="*60)
    print(f"🎯 Next {limit} Tasks (Priority)")
    print("="*60)
    
    # Get open issues sorted by milestone and labels
    issues = get_issues(state="open")
    
    # Priority order: foundation > core > enhancement
    priority_labels = ['foundation', 'core', 'enhancement']
    
    sorted_issues = sorted(issues, key=lambda x: (
        x['milestone']['title'] if x['milestone'] else 'zzz',
        min([priority_labels.index(l['name']) if l['name'] in priority_labels else 999 for l in x['labels']] + [999])
    ))
    
    for i, issue in enumerate(sorted_issues[:limit], 1):
        milestone = issue['milestone']['title'] if issue['milestone'] else "No milestone"
        labels = ", ".join([l['name'] for l in issue['labels']])
        
        print(f"\n{i}. #{issue['number']}: {issue['title']}")
        print(f"   📌 Milestone: {milestone}")
        print(f"   🏷️  Labels: {labels}")
        print(f"   🔗 {issue['html_url']}")

def show_stats():
    """Show repository statistics"""
    print("\n" + "="*60)
    print("📊 Repository Statistics")
    print("="*60)
    
    issues = get_issues(state="all")
    
    total = len(issues)
    open_count = len([i for i in issues if i['state'] == 'open'])
    closed_count = len([i for i in issues if i['state'] == 'closed'])
    
    print(f"\nTotal issues: {total}")
    print(f"  ✅ Closed: {closed_count} ({closed_count/total*100:.1f}%)")
    print(f"  🔴 Open: {open_count} ({open_count/total*100:.1f}%)")
    
    # By milestone
    print("\nBy Milestone:")
    milestones_response = requests.get(f"{BASE_URL}/milestones", headers=HEADERS, params={"state": "all"})
    milestones = milestones_response.json() if milestones_response.status_code == 200 else []
    
    for milestone in milestones:
        total_m = milestone['open_issues'] + milestone['closed_issues']
        if total_m > 0:
            progress = milestone['closed_issues'] / total_m * 100
            print(f"  {milestone['title']}: {milestone['closed_issues']}/{total_m} ({progress:.0f}%)")

def main():
    """Main CLI"""
    if len(sys.argv) < 2:
        print("GitHub Issues Manager")
        print("\nUsage:")
        print("  python3 manage_issues.py <command>")
        print("\nCommands:")
        print("  open          - List all open issues")
        print("  closed        - List recently closed issues")
        print("  milestones    - List issues by milestone")
        print("  next [N]      - Show next N tasks (default: 5)")
        print("  stats         - Show repository statistics")
        print("\nExamples:")
        print("  python3 manage_issues.py open")
        print("  python3 manage_issues.py next 10")
        print("  python3 manage_issues.py stats")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "open":
            list_open_issues()
        elif command == "closed":
            list_closed_issues()
        elif command == "milestones":
            list_by_milestone()
        elif command == "next":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            next_tasks(limit)
        elif command == "stats":
            show_stats()
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
