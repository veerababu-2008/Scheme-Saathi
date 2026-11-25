import os
import re
from pathlib import Path

frontend_dir = Path(r"d:\SchemeSaathi\frontend")
html_files = list(frontend_dir.rglob("*.html"))

issues = []

for hf in html_files:
    content = hf.read_text(encoding="utf-8")
    rel_path = hf.relative_to(frontend_dir)

    # 1. Check <link href="...">
    for m in re.finditer(r'<link[^>]+href=["\']([^"\']+)["\']', content):
        href = m.group(1).split("?")[0].split("#")[0]
        if href.startswith(("http://", "https://", "data:", "#")):
            continue
        if href.startswith("/"):
            target = (frontend_dir / href.lstrip("/")).resolve()
        else:
            target = (hf.parent / href).resolve()
        if not target.exists():
            issues.append(f"[{rel_path}] Broken stylesheet link: {href}")

    # 2. Check <script src="...">
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', content):
        src = m.group(1).split("?")[0].split("#")[0]
        if src.startswith(("http://", "https://", "data:")):
            continue
        if src.startswith("/"):
            target = (frontend_dir / src.lstrip("/")).resolve()
        else:
            target = (hf.parent / src).resolve()
        if not target.exists():
            issues.append(f"[{rel_path}] Broken script src: {src}")

    # 3. Check getElementById in inline scripts
    inline_scripts = re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', content, flags=re.DOTALL)
    ids_in_html = set(re.findall(r'id=["\']([^"\']+)["\']', content))
    for scr in inline_scripts:
        for id_match in re.finditer(r'document\.getElementById\(["\']([^"\']+)["\']\)', scr):
            elem_id = id_match.group(1)
            if elem_id not in ids_in_html:
                issues.append(f"[{rel_path}] document.getElementById('{elem_id}') not found in HTML markup!")

    # 4. Check querySelector('#...')
    for scr in inline_scripts:
        for qs_match in re.finditer(r'document\.querySelector\(["\']#([^"\'\s,>+~:]+)["\']\)', scr):
            elem_id = qs_match.group(1)
            if elem_id not in ids_in_html:
                issues.append(f"[{rel_path}] document.querySelector('#{elem_id}') not found in HTML markup!")

print(f"Total HTML files scanned: {len(html_files)}")
print(f"Issues found: {len(issues)}")
for iss in issues:
    print("  -", iss)
