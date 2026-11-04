# Trades website template

One template, one config per business, one demo site each. Built for local trades (roofers, electricians, gardeners, plumbers, cleaners) that have strong Google reviews but no website.

## Make a new demo (about 15 minutes)

1. **Qualify the lead on Google Maps:** 15+ reviews, rating 4.7+, phone listed, and **no Website button** (a Facebook page counts as no website).
2. **Add an entry to `leads.json`** (copy an existing one). Fill in from their Maps listing:
   - `slug` (folder name, e.g. `cork-roofers`), `business`, `trade`, `trade_plural`, `town`, `county`
   - `phone`, `whatsapp` (digits only with country code, e.g. `353857388411`), `hours`
   - `rating`, `review_count`, `google_url` (their Maps link)
   - `reviews`: 3 real Google reviews, copied word for word. Short ones that mention punctuality, tidiness or price work best.
   - `services`, `areas`, `headline`, `subline`, `promises`, `accent` (brand colour)
3. **Build:** `python3 build.py cork-roofers` (or `python3 build.py` for all). Output: `demos/<slug>/index.html`.
4. **Open the file in a browser and check it** on desktop and phone width.
5. **Push.** The demo is live at `<your-domain>/<slug>/` once the repo is deployed (Vercel or Cloudflare Pages, with `demos/` as the output directory).

Any field you leave out falls back to the defaults in `template.html`.

## Icons available for services

`roof` `layers` `drop` `home` `bolt` `search` `leaf` `wrench` `brush` `tree` `sparkle` `tap` `sun` `check` `phone` `clock` `pin` `shield` `mail`

## Rules (keep these, they protect the pitch)

- **Real data only.** Reviews, rating and review count must come from their own Google listing. Never write a review. `promises` must be things their reviews actually say (punctual, tidy, photos of issues, and so on); the owner confirms them on the call.
- **Demos are private previews.** Every page has `noindex` and a "Preview built for ..." banner (`demo_banner: true`). Turn the banner off only for a paying client's live site.
- **If they say no, delete their folder** and push. It's their business name, number and reviews.
- **Paying clients move to their own project and domain** (e.g. `corkroofers.ie`), not a shared demo link.

## Sending it

> Hi James, saw Cork Roofers on Google: 92 reviews at 4.9, which is brilliant. But anyone who Googles you after a recommendation has nothing to click. I built you a quick site from your own reviews: [link]. If you like it, I can make it yours this week.

Send it on WhatsApp or by text to the number on their listing, around 9 to 10am local time.
