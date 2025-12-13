#!/bin/bash
# Import Agent Pipeline Issues to GitHub

REPO="leval907/financial-methodologies-kb"
MILESTONE="Agent Pipeline v0.5"

# Check if milestone exists, create if not
MILESTONE_NUMBER=$(gh api repos/$REPO/milestones --jq ".[] | select(.title==\"$MILESTONE\") | .number")

if [ -z "$MILESTONE_NUMBER" ]; then
  echo "Creating milestone: $MILESTONE"
  MILESTONE_NUMBER=$(gh api repos/$REPO/milestones -f title="$MILESTONE" -f description="AI-powered pipeline for automated methodology extraction from books" --jq '.number')
  echo "Created milestone #$MILESTONE_NUMBER"
fi

# Import issues
echo "Importing Agent Pipeline issues..."

jq -c '.[]' issues_agent_pipeline.json | while read issue; do
  TITLE=$(echo $issue | jq -r '.title')
  BODY=$(echo $issue | jq -r '.body')
  LABELS=$(echo $issue | jq -r '.labels | join(",")')
  ISSUE_MILESTONE=$(echo $issue | jq -r '.milestone')
  
  # Determine milestone number
  if [ "$ISSUE_MILESTONE" == "$MILESTONE" ]; then
    MILESTONE_FLAG="--milestone $MILESTONE_NUMBER"
  else
    MILESTONE_FLAG=""
  fi
  
  echo "Creating issue: $TITLE"
  gh issue create \
    --repo $REPO \
    --title "$TITLE" \
    --body "$BODY" \
    --label "$LABELS" \
    $MILESTONE_FLAG
  
  sleep 1
done

echo "✅ Agent Pipeline issues imported successfully!"
