# sethkrch.com

Web-design studio site for Seth Krch. Served by GitHub Pages from the root of
`main`, with the custom domain set in `CNAME`. Everything is static HTML with no
build step.

| Path | What it is |
|---|---|
| `index.html` | Studio home page: live contour-map hero, 3D carousel of work, pricing, contact |
| `portfolio/` | All projects grouped by category (business sites, experiments, developer and tools) with a filter. Cards are listed in the page itself |
| `work/krch-auto/` | Krch Auto concept site (the "Bold" design) |
| `work/bright-shine/` | Bright Shine Family Dental, a demo site for a fictional practice |
| `work/singularity/` | Copy of the developer portfolio, whose home is krch.dev |
| `work/cinder-and-crust/` | Cinder & Crust, a concept site for a fictional wood-fired pizzeria (not in the carousel) |
| `work/pale-elysium/` | Pale Elysium, a vaporwave sculpture garden: raymarched marble bust, three skies, synthesized mixtape (WebGL, not in the carousel) |
| `work/cathode-archive/` | Cathode Archive, a CRT terminal with a dithered stone bust you can chisel (WebGL, not in the carousel) |
| `work/thumbs/` | Screenshots used by the carousel |
| `kit/` | Element kit: live components shown before/after, themeable as auto shop, dentist, café or salon |

The carousel list lives in the `WORK` array near the end of `index.html`. To add
a site, drop a 1280×800 screenshot in `work/thumbs/` and add an entry there.
The portfolio page lists every project as a card inside its category section in
`portfolio/index.html`; the same thumbnails are used.

All motion stops when the visitor's system has reduced motion turned on.

## Preview locally

```bash
python3 -m http.server 8000
# open http://127.0.0.1:8000
```
