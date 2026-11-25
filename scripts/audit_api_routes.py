import os
import re
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, r"d:\SchemeSaathi\backend")
from app import create_app

app = create_app("testing")
backend_routes = set()
for rule in app.url_map.iter_rules():
    methods = rule.methods - {"OPTIONS", "HEAD"}
    method = list(methods)[0] if methods else "GET"
    backend_routes.add((method, str(rule.rule)))

print(f"Total backend routes: {len(backend_routes)}")

# Find all api calls in frontend
frontend_dir = Path(r"d:\SchemeSaathi\frontend")
api_calls = []
for p in list(frontend_dir.rglob("*.html")) + list(frontend_dir.rglob("*.js")):
    text = p.read_text(encoding="utf-8")
    for m in re.finditer(r"api\.(get|post|put|patch|delete)\([\"']([^\"']+)[\"']", text):
        method = m.group(1).upper()
        url = m.group(2)
        api_calls.append((method, url, p.name))

print(f"Total frontend API calls found: {len(api_calls)}")
unmatched = []
for method, url, fname in api_calls:
    # normalize url with /api/v1 prefix
    full_url = f"/api/v1{url}" if not url.startswith("http") and not url.startswith("/api/v1") else url
    # strip query params
    full_url_no_query = full_url.split("?")[0]
    matched = False
    for b_method, b_rule in backend_routes:
        rule_regex = "^" + re.sub(r"<[^>]+>", r"[^/]+", b_rule).rstrip("/") + "/?$"
        if re.match(rule_regex, full_url_no_query.rstrip("/") + "/"):
            matched = True
            break
    if not matched:
        unmatched.append((fname, method, url, full_url))

if unmatched:
    print(f"Found {len(unmatched)} unmatched API calls:")
    for fname, method, url, full_url in unmatched:
        print(f"  [{fname}] {method} {url} -> {full_url}")
else:
    print("All frontend API calls matched backend routes successfully!")
