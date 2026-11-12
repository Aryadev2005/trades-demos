#!/usr/bin/env python3
"""Find trades on Google with no website, make demo sites for the best, write an outreach sheet.

    export GOOGLE_MAPS_API_KEY=...                 # Places API (New), billed project
    python3 scripts/places_to_trades.py --dry-run  # search + rank only
    python3 scripts/places_to_trades.py            # make demos (default from prospects.json)

Same idea as salon-demos/scripts/places_to_leads.py, adapted to this repo's leads.json:
  search queries -> keep open businesses with a mobile or phone, no real website, rating and
  review thresholds -> rank (WhatsApp-able mobiles first, then rating x log reviews) -> for each:
  5 photos (hero + 4 work), real Google reviews (first names), hours, nearby areas, services for
  the trade -> append to leads.json -> build.py -> out/outreach.csv.

Never claims insurance, accreditations, guarantees or years in business: only facts from Google.
Raw Google responses are cached in cache/places/ (git-ignored); --max-requests caps a run.
"""
import argparse
import csv
import json
import math
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "places"
OUT = ROOT / "out"
LEADS = ROOT / "leads.json"
CONFIG = ROOT / "scripts" / "prospects.json"
API = "https://places.googleapis.com/v1"
DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

FIELDS = ",".join("places." + f for f in [
    "id", "displayName", "formattedAddress", "addressComponents", "nationalPhoneNumber",
    "internationalPhoneNumber", "rating", "userRatingCount", "regularOpeningHours", "websiteUri",
    "googleMapsUri", "reviews", "photos", "primaryType", "types", "businessStatus",
]) + ",nextPageToken"

NOT_A_WEBSITE = ["facebook.com", "fb.com", "instagram.com", "linktr.ee", "checkatrade.com", "mybuilder.com",
                 "ratedpeople.com", "trustatrader.com", "yell.com", "bark.com", "wa.me", "tiktok.com",
                 "business.site", "google.com", "g.page"]
CHAINS = ["british gas", "dyno", "pimlico", "aspect", "mr electric", "rescue my", "homeserve", "warmzilla",
          "boxt", "drain", "anglian", "everest", "safestyle", "checkatrade"]

TRADES = {  # primary type -> wording and starter services (no claims)
    "roofing_contractor": dict(trade="Roofer", plural="Roofing", accent="#9A4A2E", services=[
        ("Roof repairs", "Slipped tiles, leaks and storm damage found and fixed."),
        ("Flat roofs", "Felt, rubber and GRP flat roofs repaired or replaced."),
        ("Gutters & fascias", "Gutters, soffits and fascias cleared, repaired or renewed."),
        ("Chimney work", "Flashing, pointing and chimney repairs."),
        ("New roofs", "Strip and re-roof with a clear plan and price.")]),
    "general_contractor": dict(trade="Builder", plural="Building", accent="#3E5C76", services=[
        ("Extensions", "Single and double storey, planned with you from the start."),
        ("Renovations", "Kitchens, bathrooms and full refurbishments."),
        ("Brickwork", "Walls, repointing and repairs."),
        ("Groundwork", "Foundations, drainage and driveways."),
        ("Small works", "Repairs and alterations, no job too small.")]),
    "plumber": dict(trade="Plumber", plural="Plumbing", accent="#2F5F8A", services=[
        ("Leaks & repairs", "Dripping taps, burst pipes and leaks fixed."),
        ("Bathrooms", "New bathrooms and showers fitted."),
        ("Boilers & heating", "Radiators, heating and boiler work."),
        ("Drains & blockages", "Sinks, toilets and drains unblocked."),
        ("Emergency call-outs", "Water where it shouldn't be? Call us.")]),
    "electrician": dict(trade="Electrician", plural="Electrical", accent="#3A4F8C", services=[
        ("Rewires", "Full and partial rewires, done tidily."),
        ("Fuse boards", "Consumer unit upgrades."),
        ("Lighting & sockets", "New lights, sockets and outdoor power."),
        ("EV chargers", "Home car charger installation."),
        ("Fault finding", "Trips, flickers and dead circuits traced and fixed.")]),
    "painter": dict(trade="Painter & decorator", plural="Painting & decorating", accent="#5B4B8A", services=[
        ("Interior painting", "Walls, ceilings and woodwork."),
        ("Exterior painting", "Render, fascias, doors and windows."),
        ("Wallpapering", "Feature walls and full rooms."),
        ("Commercial", "Shops, offices and rentals.")]),
}
ALIASES = {"roofing": "roofing_contractor", "builder": "general_contractor", "construction_company": "general_contractor",
           "contractor": "general_contractor", "plumbing": "plumber", "electrical": "electrician", "painting": "painter"}

NEARBY = {  # town -> areas listed on the page
    "Wigan": ["Wigan", "Standish", "Orrell", "Pemberton", "Hindley", "Ince", "Aspull", "Shevington", "Ashton-in-Makerfield"],
    "Leigh": ["Leigh", "Atherton", "Tyldesley", "Golborne", "Lowton", "Astley", "Hindley"],
    "Bolton": ["Bolton", "Horwich", "Westhoughton", "Farnworth", "Little Lever", "Bromley Cross", "Kearsley"],
    "Chorley": ["Chorley", "Euxton", "Adlington", "Coppull", "Whittle-le-Woods", "Buckshaw Village", "Leyland"],
    "St Helens": ["St Helens", "Rainford", "Haydock", "Newton-le-Willows", "Eccleston", "Billinge", "Prescot"],
    "Warrington": ["Warrington", "Great Sankey", "Penketh", "Birchwood", "Lymm", "Culcheth", "Stockton Heath"],
    "Widnes": ["Widnes", "Runcorn", "Halebank", "Hough Green", "Cronton", "Warrington", "St Helens"],
    "Harrogate": ["Harrogate", "Knaresborough", "Ripon", "Pannal", "Killinghall", "Boroughbridge", "Wetherby", "Pateley Bridge"],
    "Keighley": ["Keighley", "Silsden", "Haworth", "Bingley", "Skipton", "Cross Hills", "Oxenhope"],
    "Ilkley": ["Ilkley", "Ben Rhydding", "Burley-in-Wharfedale", "Addingham", "Otley", "Menston"],
    "Skipton": ["Skipton", "Gargrave", "Embsay", "Grassington", "Settle", "Cononley"],
    "Wetherby": ["Wetherby", "Boston Spa", "Collingham", "Harrogate", "Tadcaster"],
    "Tetbury": ["Tetbury", "Malmesbury", "Cirencester", "Nailsworth", "Avening"],
    "Knaresborough": ["Knaresborough", "Harrogate", "Boroughbridge", "Ripon", "Wetherby"],
    "Ripon": ["Ripon", "Harrogate", "Masham", "Boroughbridge", "Knaresborough", "Pateley Bridge"],
    "Cirencester": ["Cirencester", "Tetbury", "Fairford", "Stroud", "Bourton-on-the-Water", "Lechlade", "Malmesbury"],
    "Stroud": ["Stroud", "Nailsworth", "Painswick", "Minchinhampton", "Cirencester", "Stonehouse"],
    "Chipping Norton": ["Chipping Norton", "Stow-on-the-Wold", "Moreton-in-Marsh", "Burford", "Charlbury", "Woodstock"],
    "Cheltenham": ["Cheltenham", "Bishop's Cleeve", "Winchcombe", "Prestbury", "Charlton Kings", "Cirencester"],
    "Skelmersdale": ["Skelmersdale", "Ormskirk", "Up Holland", "Parbold", "Burscough", "Aughton"],
}


COUNTY = {"Keighley": "West Yorkshire", "Ilkley": "West Yorkshire", "Skipton": "North Yorkshire", "Otley": "West Yorkshire", "Harrogate": "North Yorkshire", "Knaresborough": "North Yorkshire", "Ripon": "North Yorkshire",
          "Wetherby": "West Yorkshire", "Cirencester": "Gloucestershire", "Stroud": "Gloucestershire",
          "Tetbury": "Gloucestershire", "Cheltenham": "Gloucestershire", "Chipping Norton": "Oxfordshire",
          "Burford": "Oxfordshire", "Moreton-in-Marsh": "Gloucestershire", "Chorley": "Lancashire",
          "Widnes": "Cheshire", "St Helens": "Merseyside", "Skelmersdale": "Lancashire"}


# ---------------------------------------------------------------- small helpers
def slugify(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40].strip("-")


def host(url):
    h = urllib.parse.urlparse(url or "").netloc.lower()
    return h[4:] if h.startswith("www.") else h


def own_website(url):
    h = host(url)
    return bool(h) and not any(h == d or h.endswith("." + d) for d in NOT_A_WEBSITE)


def uk_mobile(phone):
    d = re.sub(r"\D", "", phone or "")
    if d.startswith("44"):
        d = "0" + d[2:]
    return "44" + d[1:] if re.fullmatch(r"07\d{9}", d) else ""


def tidy_name(n):
    n = re.sub(r"\s+", " ", n).strip()
    n = re.split(r"\s[-|–]\s|\s?,", n)[0]  # drop "- roofing specialists" / ", Widnes & northwest" tails
    n = re.sub(r"\s+(Ltd|Limited)$", "", n.strip(), flags=re.I)
    if n.isupper() or n.islower():
        n = " ".join(w if (w.isupper() and len(w) <= 3) else w.capitalize() for w in n.split())
    n = re.sub(r"\bMccann\b", "McCann", n)
    n = re.sub(r"\b(and|sons|roofing|guttering|services)\b", lambda m: m.group(1) if m.group(1) == "and" else m.group(1).capitalize(), n)
    return n.strip()


class Budget:
    def __init__(self, n):
        self.n, self.used = n, 0

    def spend(self, what):
        if self.used >= self.n:
            raise SystemExit(f"Stopped at --max-requests {self.n} ({what}). Re-run to continue from cache.")
        self.used += 1


def fetch(req, budget, what):
    budget.spend(what)
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and i < 2:
                time.sleep(2 * (i + 1))
                continue
            raise SystemExit(f"Google API error {e.code} on {what}: {e.read().decode('utf-8', 'replace')[:300]}")
        except urllib.error.URLError as e:
            if i < 2:
                time.sleep(2)
                continue
            raise SystemExit(f"Network error on {what}: {e}")


# ---------------------------------------------------------------- search
def search(q, key, budget, pages):
    out, token = [], None
    for page in range(pages):
        cf = CACHE / f"{slugify(q)}-p{page + 1}.json"
        if cf.exists():
            data = json.loads(cf.read_text())
        else:
            if not key:
                break
            body = {"textQuery": q, "pageSize": 20, "regionCode": "GB", "languageCode": "en"}
            if token:
                body["pageToken"] = token
                time.sleep(2)
            req = urllib.request.Request(f"{API}/places:searchText", json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "X-Goog-Api-Key": key,
                                                  "X-Goog-FieldMask": FIELDS})
            data = json.loads(fetch(req, budget, f'search "{q}" p{page + 1}'))
            CACHE.mkdir(parents=True, exist_ok=True)
            cf.write_text(json.dumps(data, indent=1))
        out += data.get("places", [])
        token = data.get("nextPageToken")
        if not token:
            break
    return out


def trade_of(p):
    for t in [p.get("primaryType", "")] + (p.get("types") or []):
        t = ALIASES.get(t, t)
        if t in TRADES:
            return t
    name = p["displayName"]["text"].lower()
    for word, t in [("roof", "roofing_contractor"), ("plumb", "plumber"), ("electric", "electrician"),
                    ("build", "general_contractor"), ("decor", "painter"), ("paint", "painter")]:
        if word in name:
            return t
    return None


def why_not(p, cfg, taken):
    name = p["displayName"]["text"]
    if p.get("businessStatus", "OPERATIONAL") != "OPERATIONAL":
        return "not operating"
    country = next((c.get("shortText") for c in p.get("addressComponents") or [] if "country" in c.get("types", [])), None)
    if country and country != "GB":
        return "other country"
    if p["id"] in taken or slugify(tidy_name(name)) in taken:
        return "already a lead"
    if any(c in name.lower() for c in CHAINS):
        return "chain"
    if not trade_of(p):
        return "not a target trade"
    if (p.get("rating") or 0) < cfg["min_rating"]:
        return "low rating"
    if (p.get("userRatingCount") or 0) < cfg["min_reviews"]:
        return "too few reviews"
    if own_website(p.get("websiteUri")):
        return "has a website"
    if not p.get("nationalPhoneNumber"):
        return "no phone"
    if len(p.get("photos") or []) < 4:
        return "too few photos"
    if len(good_reviews(p)) < 2:
        return "too few usable reviews"
    return None


def score(p):
    s = (p.get("rating") or 0) * math.log10(1 + (p.get("userRatingCount") or 0))
    return s + (2 if uk_mobile(p.get("nationalPhoneNumber")) else 0)


# ---------------------------------------------------------------- lead fields
def good_reviews(p):
    out, seen = [], set()
    for r in sorted(p.get("reviews") or [], key=lambda r: -(r.get("rating") or 0)):
        if (r.get("rating") or 0) < 5:
            continue
        t = re.sub(r"\s+", " ", ((r.get("originalText") or r.get("text") or {}).get("text") or "")).strip()
        if len(t) > 240:
            cut = t[:240]
            m = max(cut.rfind(". "), cut.rfind("! "))
            t = cut[:m + 1] if m > 60 else ""
        n = ((r.get("authorAttribution") or {}).get("displayName") or "").split()
        first = n[0].strip(".,") if n else ""
        first = first[:1].upper() + first[1:] if first.isalpha() and len(first) > 1 else ""
        if len(t) < 40 or not first or first in seen:
            continue
        seen.add(first)
        out.append({"name": first, "text": t})
        if len(out) == 3:
            break
    return out


def town_of(p):
    comp = {}
    for c in p.get("addressComponents") or []:
        for t in c.get("types", []):
            comp.setdefault(t, c.get("longText"))
    town = comp.get("postal_town") or comp.get("locality") or ""
    return "St Helens" if town == "Saint Helens" else town


def share_suffix(m):
    """Google writes '8:00 to 11:00am': give the first time its own am/pm."""
    h1, m1, h2, m2, suf = int(m.group(1)), m.group(2), int(m.group(3)), m.group(4), m.group(5)
    first = suf if (h1 % 12) <= (h2 % 12) else ("am" if suf == "pm" else "pm")
    return f"{h1}:{m1}{first} to {h2}:{m2}{suf}"


def hours_text(p):
    """Group Google's own day lines: 'Mon to Fri 8am to 5pm, Sat 8am to 1pm'."""
    lines = (p.get("regularOpeningHours") or {}).get("weekdayDescriptions") or []
    if len(lines) != 7:
        return "Call or WhatsApp for times"
    days, vals = [], []
    for ln in lines:
        d, _, v = ln.partition(": ")
        v = v.replace("\u2009", " ").replace("\u202f", " ").replace(" – ", " to ").replace("–", " to ").replace(" AM", "am").replace(" PM", "pm")
        v = re.sub(r"(\d{1,2}):(\d{2}) to (\d{1,2}):(\d{2})([ap]m)", share_suffix, v)
        v = re.sub(r":00(?=[ap]m)", "", v).replace("Open 24 hours", "open 24 hours")
        days.append(d[:3])
        vals.append(v)
    if all(v == "open 24 hours" for v in vals):
        return "Open 24 hours, 7 days"
    groups = []
    for d, v in zip(days, vals):
        if groups and groups[-1][2] == v:
            groups[-1][1] = d
        else:
            groups.append([d, d, v])
    parts = [f"{a if a == b else a + ' to ' + b} {v}" for a, b, v in groups if v != "Closed"]
    return ", ".join(parts)[:1].upper() + ", ".join(parts)[1:]


def get_photos(p, slug, key, budget, n):
    folder = ROOT / "demos" / slug / "img"
    folder.mkdir(parents=True, exist_ok=True)
    photos = p.get("photos") or []
    # hero: the widest photo (landscape suits the full-width hero)
    order = sorted(range(len(photos)), key=lambda i: -(photos[i].get("widthPx", 1) / max(photos[i].get("heightPx", 1), 1)))
    picks = [order[0]] + [i for i in range(len(photos)) if i != order[0]][:n - 1]
    paths, credits = [], set()
    from PIL import Image
    for k, i in enumerate(picks):
        ph = photos[i]
        for a in ph.get("authorAttributions") or []:
            if a.get("displayName"):
                credits.add(a["displayName"])
        name = "hero.jpg" if k == 0 else f"w{k}.jpg"
        dest = folder / name
        paths.append(f"img/{name}")
        if dest.exists():
            continue
        url = f"{API}/{ph['name']}/media?" + urllib.parse.urlencode({"maxWidthPx": 1600, "maxHeightPx": 1600, "key": key})
        tmp = folder / (name + ".part")
        tmp.write_bytes(fetch(urllib.request.Request(url), budget, f"photo {slug}/{name}"))
        im = Image.open(tmp).convert("RGB")
        im.thumbnail((1600, 1600))
        im.save(dest, "JPEG", quality=80, optimize=True, progressive=True)
        tmp.unlink()
    return paths, sorted(credits)


def make_lead(p, slug, cfg, photos):
    t = TRADES[trade_of(p)]
    name = tidy_name(p["displayName"]["text"])
    town = town_of(p) or cfg.get("default_town", "Wigan")
    phone = p.get("nationalPhoneNumber", "")
    wa = uk_mobile(phone)
    rating, count = round(p.get("rating") or 0, 1), p.get("userRatingCount") or 0
    areas = NEARBY.get(town, [town])
    reviews = good_reviews(p)
    return {
        "slug": slug, "business": name, "trade": t["trade"], "trade_plural": t["plural"],
        "town": town, "county": COUNTY.get(town, cfg.get("county", "Greater Manchester")), "coverage": f"{town} and nearby",
        "phone": phone, "whatsapp": wa, "rating": rating, "review_count": count,
        "google_url": p.get("googleMapsUri", ""), "hours": hours_text(p), "accent": t["accent"],
        "photos": photos,
        "headline": f"{t['plural']} in {town}, done properly.",
        "subline": f"{name}: rated {rating:.1f} from {count} Google reviews. "
                   + ("Call, WhatsApp or send the form for a free quote." if wa else "Call or send the form for a free quote."),
        "promises": [f"Rated {rating:.1f} on Google", f"{count} Google reviews", f"Based in {town}", "Free quotes"],
        "services": [{"name": a, "text": b} for a, b in t["services"]],
        "reviews": reviews,
        "areas": areas,
        "built_by": cfg["your_name"],
        "place_id": p["id"],
        "_auto": True,
    }


# The jobs each trade makes the most money from: the pitch leads with these, not with "a website".
MONEY = {
    "roof": ("more re-roofs and repair jobs", "full re-roofs, storm and leak repairs, flat roofs and fascias"),
    "plumb": ("more boiler installs and bathroom jobs", "boiler installs and swaps, bathrooms and emergency call-outs"),
    "electric": ("more rewires and bigger electrical jobs", "rewires, fuse board upgrades and EV chargers"),
    "build": ("more extension and renovation enquiries", "extensions, renovations and bigger building jobs"),
    "handy": ("more steady local jobs", "electrics, decorating and the bigger jobs on people's lists"),
    "paint": ("more full-house decorating jobs", "full interiors, exteriors and commercial work"),
}


def money_for(trade):
    t = trade.lower()
    for k, v in MONEY.items():
        if k in t:
            return v
    return ("more local jobs", "the bigger jobs in your area")


def sheet(rows_leads, cfg):
    OUT.mkdir(exist_ok=True)
    rows = []
    for l in rows_leads:
        demo = f"{cfg['base_url'].rstrip('/')}/{l['slug']}/"
        short, long_ = money_for(l["trade"])
        price, monthly = cfg["price"], cfg.get("monthly", 39)
        terms = (f"you only pay once it's live and you're happy with it: £{price} once, or £{monthly} a month "
                 f"with no contract")
        opener = (f"Hi, is this {l['business']}? I'm {cfg['your_name']}. I made a free website for you, built to bring in "
                  f"{short}, using your own Google reviews ({l['rating']:.1f} from {l['review_count']}). Nothing to pay "
                  f"or sign up for. Can I send you the link?")
        after_yes = (f"Here it is: {demo}\n\nIt's built around the jobs that pay best: {long_}. There's a quote form "
                     f"that sends each enquiry straight to your WhatsApp, with the job, postcode and details, so you can "
                     f"price it before you call back. I've used your own reviews and photos, so there's nothing for you to do.\n\n"
                     f"If you want it, I'll put it live on your Google listing, and {terms}. Happy to change anything first.")
        follow_up = (f"Hi again, {cfg['your_name']} here. One thing I should have made clear about the website I made for "
                     f"{l['business']}: there's no risk. I'll put it live on your Google listing and {terms}. It's built "
                     f"to bring in {short}: {demo}\n\nNo worries at all if it's not for you.")
        contacted = bool(l.get("contacted"))
        first = follow_up if contacted else opener
        rows.append({"business": l["business"], "trade": l["trade"], "town": l["town"], "rating": l["rating"],
                     "reviews": l["review_count"], "phone": l["phone"],
                     "stage": "already messaged: send follow-up" if contacted else "new: send opener",
                     "channel": "WhatsApp" if l["whatsapp"] else "Call / text",
                     "whatsapp_link": f"https://wa.me/{l['whatsapp']}?text={urllib.parse.quote(first)}" if l["whatsapp"] else "",
                     "demo": demo, "1_opener": opener, "2_after_they_say_yes": after_yes,
                     "follow_up_if_already_messaged": follow_up, "status": "", "notes": ""})
    path = OUT / "outreach.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:  # BOM so Excel/Numbers read UTF-8 (£, names)
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["business"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {path.relative_to(ROOT)}: {len(rows)} leads.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(CONFIG))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--max-requests", type=int, default=150)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rebuild-sheet", action="store_true")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    cfg.setdefault("min_rating", 4.7)
    cfg.setdefault("min_reviews", 20)
    cfg.setdefault("photos", 5)
    cfg.setdefault("pages", 2)
    limit = a.limit or cfg.get("limit", 5)
    leads = json.loads(LEADS.read_text())
    if a.rebuild_sheet:
        return sheet([l for l in leads if l.get("_auto")], cfg)
    key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not key and not any(CACHE.glob("*.json")):
        sys.exit("Set GOOGLE_MAPS_API_KEY first.")
    budget = Budget(a.max_requests)
    pool, seen = [], set()
    for q in cfg["queries"]:
        found = search(q, key, budget, cfg["pages"])
        print(f"  {len(found):3d} · {q}")
        for p in found:
            if p["id"] not in seen:
                seen.add(p["id"])
                pool.append(p)
    taken = {l.get("place_id") for l in leads} | {l["slug"] for l in leads} | {slugify(s) for s in cfg.get("skip", [])}
    rej, keep = {}, []
    for p in pool:
        w = why_not(p, cfg, taken)
        if w:
            rej[w] = rej.get(w, 0) + 1
        else:
            keep.append(p)
    keep.sort(key=score, reverse=True)
    pick = keep[:limit]
    print(f"\n{len(pool)} unique, {len(keep)} qualify, making {len(pick)}.")
    print("  skipped: " + ", ".join(f"{v} {k}" for k, v in sorted(rej.items(), key=lambda x: -x[1])))
    for p in keep[:limit + 10]:
        mark = "→" if p in pick else " "
        print(f"  {mark} {p.get('rating')}★ {p.get('userRatingCount'):>4}  {tidy_name(p['displayName']['text'])}  ·  "
              f"{TRADES[trade_of(p)]['trade']}, {town_of(p)}  ·  {p.get('nationalPhoneNumber')}"
              f"{'  · WhatsApp' if uk_mobile(p.get('nationalPhoneNumber')) else ''}")
    if a.dry_run:
        print(f"\nDry run: {budget.used} Google requests. Nothing written.")
        return
    used = {l["slug"] for l in leads}
    new = []
    for p in pick:
        base = slugify(tidy_name(p["displayName"]["text"]))
        town = slugify(town_of(p))
        slug = base if (not town or town in base) else f"{base}-{town}"
        while slug in used:
            slug += "-2"
        used.add(slug)
        photos, _ = get_photos(p, slug, key, budget, cfg["photos"])
        new.append(make_lead(p, slug, cfg, photos))
        print(f"  ✓ {slug}")
    leads += new
    LEADS.write_text(json.dumps(leads, indent=2, ensure_ascii=False) + "\n")
    subprocess.run([sys.executable, str(ROOT / "build.py")] + [l["slug"] for l in new], check=True)
    sheet([l for l in leads if l.get("_auto")], cfg)
    print(f"{budget.used} Google requests used.")


if __name__ == "__main__":
    main()
