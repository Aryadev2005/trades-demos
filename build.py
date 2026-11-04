"""Build one demo site per lead.

Usage:
    python3 build.py                 # builds every lead in leads.json
    python3 build.py cork-roofers    # builds one lead by its slug

Output: demos/<slug>/index.html (ready to deploy to Vercel or GitHub Pages).
Any field a lead leaves out falls back to the template's default config.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
TEMPLATE = (HERE / "template.html").read_text(encoding="utf-8")
LEADS = json.loads((HERE / "leads.json").read_text(encoding="utf-8"))

match = re.search(r"/\*CONFIG\*/(.*?)/\*END\*/", TEMPLATE, re.S)
DEFAULTS = json.loads(match.group(1))


def build(lead: dict) -> Path:
    slug = lead["slug"]
    cfg = {**DEFAULTS, **{k: v for k, v in lead.items() if k != "slug"}}
    # Fill sensible defaults the lead didn't override
    cfg.setdefault("headline", f"{cfg['trade']} in {cfg['town']} you can rely on.")
    data = json.dumps(cfg, ensure_ascii=False, indent=2).replace("</", "<\\/")
    html = TEMPLATE[: match.start(1)] + data + TEMPLATE[match.end(1):]
    out = HERE / "demos" / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    wanted = set(sys.argv[1:])
    for lead in LEADS:
        if wanted and lead["slug"] not in wanted:
            continue
        missing = [k for k in ("business", "trade", "town", "phone") if not lead.get(k)]
        if missing:
            print(f"skip {lead.get('slug')}: missing {', '.join(missing)}")
            continue
        print("built", build(lead))
