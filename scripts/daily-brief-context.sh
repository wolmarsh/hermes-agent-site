#!/usr/bin/env bash
# Daily brief data collector — fetches news headlines for the cron agent
set -euo pipefail

echo "=== DAILY BRIEF CONTEXT ==="
echo "Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""

# Fetch top AI news stories
echo "--- Top AI News ---"
curl -s "https://hn.algolia.com/api/v1/search?query=AI+artificial+intelligence&tags=story&hitsPerPage=10&numericFilters=created_at_i>$(date -d '24 hours ago' +%s)" 2>/dev/null | \
  python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for i, hit in enumerate(data.get('hits', [])[:5], 1):
        title = hit.get('title', '')
        url = hit.get('url', '') or f'https://news.ycombinator.com/item?id={hit.get(\"objectID\", \"\")}'
        points = hit.get('points', 0)
        print(f'{i}. {title} ({points} pts)')
        print(f'   {url}')
        print()
except: pass
" 2>/dev/null || echo "(HN API unavailable)"

echo ""
echo "--- Dev.to Cross-Posting Available ---"
echo "To cross-post the latest article: python3 scripts/crosspost.py"
echo "List articles: python3 scripts/crosspost.py --list"
echo "Post specific: python3 scripts/crosspost.py --post <index>"
echo ""

echo "--- Today's Date Info ---"
date -u '+%A, %B %d, %Y'
echo "Timezone: $(cat /etc/timezone 2>/dev/null || echo 'UTC')"
echo ""
echo "=== END CONTEXT ==="
