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
from html import escape
from pathlib import Path

# Where the demos are deployed. Used for absolute link-preview URLs.
BASE_URL = "https://trades-demos.vercel.app"

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
    # Bake title + link-preview tags into the HTML. WhatsApp, iMessage and Facebook
    # build previews without running JavaScript, so these must be in the file itself.
    e = lambda s: escape(str(s), quote=True)
    page_url = f"{BASE_URL}/{slug}/"
    title = f"{cfg['business']} | {cfg['trade']} in {cfg['town']}"
    desc = f"{cfg['rating']:.1f} stars from {cfg['review_count']} Google reviews. {cfg['subline']}"
    meta = [
        f"<title>{e(title)}</title>",
        f'<meta name="description" content="{e(desc)}">',
        f'<meta property="og:type" content="website">',
        f'<meta property="og:url" content="{e(page_url)}">',
        f'<meta property="og:title" content="{e(title)}">',
        f'<meta property="og:description" content="{e(desc)}">',
    ]
    photos = cfg.get("photos") or []
    if photos:
        img = photos[0] if photos[0].startswith("http") else page_url + photos[0].lstrip("./")
        meta += [f'<meta property="og:image" content="{e(img)}">',
                 '<meta name="twitter:card" content="summary_large_image">']
    html = html.replace("<title>Loading…</title>", "\n".join(meta), 1)
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
