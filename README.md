# Trades website template

One template, one config per business, one demo site each. Built for local trades (roofers, electricians, gardeners, plumbers, cleaners) that have strong Google reviews but no website.

## Find leads and make demos automatically

```bash
export GOOGLE_MAPS_API_KEY=...                  # Places API (New), billed Google Cloud project
python3 scripts/places_to_trades.py --dry-run   # search + rank: see who qualifies
python3 scripts/places_to_trades.py             # make demos (limit in scripts/prospects.json)
git add leads.json demos && git commit -m "New demos" && git push   # Vercel deploys on push
```

- Searches come from `scripts/prospects.json` (roofers, builders, plumbers, electricians around Wigan).
- Kept: operating, rating ≥ 4.7, ≥ 20 reviews, phone listed, at least 4 photos and 2 usable five-star
  reviews, and **no own website** (Facebook, Checkatrade, MyBuilder, Rated People, Yell etc. don't count).
  Ranked by rating × log(reviews), with UK mobiles (WhatsApp-able) first.
- Each lead gets: real rating, review count, Google's opening hours, 3 five-star reviews (first names),
  5 Google photos (widest as hero), nearby areas for the town, and starter services for the trade.
  **Promises are only facts from Google** (rating, review count, town, free quotes): never insurance,
  accreditations, guarantees or years trading.
- `out/outreach.csv` (git-ignored): phone, a WhatsApp click-to-send link with the message filled in, demo link.
- Google responses are cached in `cache/places/` (git-ignored), so re-runs are free; `--max-requests` caps a run.
- Always look at the photos before sending: stock clip-art, adverts with phone numbers and letterboxed
  screenshots slip in. Remove them from the lead's `photos` list and run `python3 build.py <slug>`.

## Make a new demo by hand (about 15 minutes)

1. **Qualify the lead on Google Maps:** 15+ reviews, rating 4.7+, phone listed, and **no Website button** (a Facebook page counts as no website).
2. **Add an entry to `leads.json`** (copy an existing one). Fill in from their Maps listing:
   - `slug` (folder name, e.g. `cork-roofers`), `business`, `trade`, `trade_plural`, `town`, `county`
   - `phone`, `whatsapp` (digits only with country code, e.g. `353857388411`), `hours`
   - `rating`, `review_count`, `google_url` (their Maps link)
   - `reviews`: 3 real Google reviews, copied word for word. Short ones that mention punctuality, tidiness or price work best.
   - `services` (name + one line each, 4 to 5 works best), `areas`, `headline`, `subline`, `promises`
   - `accent`: one muted brand colour (copper, deep blue, forest green). Avoid bright neon tones; they cheapen the look.
   - `photos` (optional, the biggest upgrade): paths to 3 to 7 photos of their own work, e.g. `["img/1.jpg", ...]` saved in `demos/<slug>/img/`. The first becomes a full-width hero, the rest a "Recent work" gallery. Take them from the photos the owner posted on their Google listing or Facebook page.
3. **Build:** `python3 build.py cork-roofers` (or `python3 build.py` for all). Output: `demos/<slug>/index.html`.
4. **Open the file in a browser and check it** on desktop and phone width.
5. **Push.** The demo is live at `<your-domain>/<slug>/` once the repo is deployed (Vercel or Cloudflare Pages, with `demos/` as the output directory).

Any field you leave out falls back to the defaults in `template.html`.

## Rules (keep these, they protect the pitch)

- **Real data only.** Reviews, rating and review count must come from their own Google listing. Never write a review. `promises` must be things their reviews actually say (punctual, tidy, photos of issues, and so on); the owner confirms them on the call.
- **Demos are private previews.** Every page has `noindex` and a "Preview built for ..." banner (`demo_banner: true`). Turn the banner off only for a paying client's live site.
- **If they say no, delete their folder** and push. It's their business name, number and reviews.
- **Paying clients move to their own project and domain** (e.g. `corkroofers.ie`), not a shared demo link.

## Sending it

> Hi James, saw Cork Roofers on Google: 92 reviews at 4.9, which is brilliant. But anyone who Googles you after a recommendation has nothing to click. I built you a quick site from your own reviews: [link]. If you like it, I can make it yours this week.

Send it on WhatsApp or by text to the number on their listing, around 9 to 10am local time.
