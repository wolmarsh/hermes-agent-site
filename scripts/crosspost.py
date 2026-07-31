#!/usr/bin/env python3
"""
dev.to Cross-Poster — robust version
Extracts blog posts from index.html and publishes to dev.to.
Usage:
    python3 crosspost.py                           # post the latest article (index 0)
    python3 crosspost.py --post 3                  # post by index (0 = first/newest)
    python3 crosspost.py --list                    # list available posts
"""
import re, os, json, sys

SITE_FILE = "/home/wolmarsh/projects/hermes-agent-site/index.html"
API_KEY = "fFJwPSj9f8HQT6JVJXN8aYhw"

def extract_posts():
    """Extract posts from the JS array using line-by-line parsing."""
    with open(SITE_FILE) as f:
        lines = f.readlines()
    
    posts = []
    in_posts_array = False
    in_post = False
    current = {}
    content_lines = []
    in_content = False
    content_open = False
    
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        
        # Detect posts array start
        if "const posts = [" in stripped:
            in_posts_array = True
            continue
        
        if not in_posts_array:
            continue
        
        # End of posts array
        if stripped.strip() == "];" and in_posts_array:
            if in_post and current:
                current["content"] = "\n".join(content_lines)
                posts.append(current)
            break
        
        # Start of a post object
        if stripped.strip() == "{" and not in_post:
            in_post = True
            current = {}
            content_lines = []
            in_content = False
            content_open = False
            continue
        
        if not in_post:
            continue
        
        # End of a post object
        if stripped.strip().startswith("}") or stripped.strip() == "},":
            if in_content and content_open:
                content_lines.append(stripped.rsplit("`", 1)[0])
                content_open = False
            if current:
                current["content"] = "\n".join(content_lines)
                posts.append(current)
            current = {}
            content_lines = []
            in_content = False
            content_open = False
            in_post = False
            continue
        
        # Handle content field (multi-line template literal)
        if in_content:
            if "`" in stripped:
                # Check if this line closes the backtick
                part = stripped[:stripped.index("`")] if content_open else ""
                before = stripped[:stripped.index("`")]
                after = stripped[stripped.index("`") + 1:]
                if content_open:
                    content_lines.append(stripped[:stripped.rindex("`")])
                    content_open = False
                    # Check if there's more after closing backtick (like , or })
                else:
                    content_lines.append(stripped[stripped.index("`") + 1:])
                    content_open = True
                    in_content = True
            else:
                if content_open:
                    content_lines.append(stripped)
            continue
        
        if "content:" in stripped:
            # Start content capture
            if "`" in stripped:
                idx = stripped.index("`")
                remaining = stripped[idx + 1:]
                if "`" in remaining:
                    # Single-line content
                    content_text = remaining[:remaining.index("`")]
                    content_lines.append(content_text)
                else:
                    content_lines.append(remaining)
                    content_open = True
                    in_content = True
            continue
        
        # Parse key-value fields
        for key in ["date", "category", "catClass", "title", "excerpt"]:
            if f"{key}:" in stripped:
                # Extract value between quotes
                m = re.search(rf"{key}:\s*'([^']*)'", stripped)
                if m:
                    val = m.group(1).replace("\\'", "'")
                    current[key] = val
    
    return posts

def html_to_markdown(html):
    """Convert blog post HTML to basic markdown for dev.to."""
    text = html
    
    # Convert <strong>text</strong> to **text**
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text)
    
    # Convert <a href="url">text</a> to [text](url)
    text = re.sub(r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text)
    
    # Convert <h3> to ### headings
    text = re.sub(r'<h3\s+[^>]*>(.*?)</h3>', r'### \1', text)
    
    # Convert <p>text</p> to text\n\n
    text = re.sub(r'<p>(.*?)</p>', r'\1\n\n', text)
    
    # Convert lists
    text = re.sub(r'<ul>(.*?)</ul>', lambda m: m.group(1), text, flags=re.DOTALL)
    text = re.sub(r'<li>(.*?)</li>', r'- \1', text)
    
    # Convert <pre> and <code>
    text = re.sub(r'<pre[^>]*>(.*?)</pre>', lambda m: f'```\n{m.group(1)}\n```', text, flags=re.DOTALL)
    text = re.sub(r'<code>(.*?)</code>', r'`\1`', text)
    
    # Remove style attributes
    text = re.sub(r' style="[^"]*"', '', text)
    
    # Clean leftover HTML
    text = re.sub(r'</?span[^>]*>', '', text)
    text = re.sub(r'</?div[^>]*>', '', text)
    text = re.sub(r'</?br\s*/?>', '\n', text)
    
    # Strip leading whitespace from every line (template literal indentation)
    text = '\n'.join(line.lstrip() for line in text.split('\n'))
    
    # Clean excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text

def post_to_devto(post, published=False):
    """Post an article to dev.to. Returns article ID on success."""
    body_markdown = html_to_markdown(post["content"])
    
    tag_map = {
        "AI": "ai",
        "Dev": "webdev", 
        "Tech": "technology",
        "Product": "productivity"
    }
    tags = [tag_map.get(post.get("category", ""), "webdev"), "machinelearning"]
    
    excerpt = post.get("excerpt", "")[:200]
    
    data = {
        "article": {
            "title": post["title"],
            "published": published,
            "body_markdown": body_markdown,
            "tags": tags[:4],
            "description": excerpt,
            "canonical_url": "https://wolmarsh.github.io/hermes-agent-site/"
        }
    }
    
    import urllib.request
    req = urllib.request.Request(
        "https://dev.to/api/articles",
        data=json.dumps(data).encode(),
        headers={
            "api-key": API_KEY,
            "Content-Type": "application/json",
            "User-Agent": "HermesAgentCrossPoster/1.0"
        },
        method="POST"
    )
    
    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        slug = result.get("url", "unknown")
        print(f"✅ Posted: \"{post['title']}\"")
        print(f"   URL: {slug}")  # dev.to returns the full URL — do NOT prefix
        print(f"   ID: {result.get('id', 'unknown')}")
        if not published:
            print("   (draft — publish from dev.to dashboard)")
        return result.get('id')
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ HTTP {e.code}: {body[:300]}")
        return None

if __name__ == "__main__":
    posts = extract_posts()
    
    if "--list" in sys.argv:
        print(f"Found {len(posts)} posts:\n")
        for i, p in enumerate(posts):
            cat = p.get("category", "?")
            title = p.get("title", "?")[:60]
            print(f"  [{i}] [{cat}] {title}")
        sys.exit(0)
    
    if len(posts) == 0:
        print("No posts found!")
        sys.exit(1)
    
    idx = 0
    if "--post" in sys.argv:
        try:
            idx = int(sys.argv[sys.argv.index("--post") + 1])
        except (ValueError, IndexError):
            print("Usage: crosspost.py [--post N | --list]")
            sys.exit(1)
    
    if idx >= len(posts):
        print(f"Index {idx} out of range (0-{len(posts)-1})")
        sys.exit(1)
    
    post = posts[idx]
    print(f"Posting: [{post.get('category','?')}] {post.get('title','?')} ({post.get('date','?')})")
    post_to_devto(post, published=False)
