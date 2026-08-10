# Portfolio

A static, dependency-free personal site. Three files, no build step.

```
portfolio/
├── index.html    # structure + content
├── styles.css    # all styling (dark, single-accent)
├── script.js     # identity CONFIG + scroll behavior
└── README.md
```

## Edit your details in one place

Open `script.js` and edit the `CONFIG` object at the top — name, role,
email, GitHub, LinkedIn, location, and per-project source links. It updates
the whole page. Nothing else needs touching for a name/link change.

To add a project source link, fill in its URL in `CONFIG.repos`, e.g.:

```js
repos: {
  "job-collector": "https://github.com/you/greenhouse-job-collector",
  ...
}
```

## Preview locally

```bash
cd portfolio
python3 -m http.server 8000
# open http://127.0.0.1:8000
```

## Deploy (pick one, all free)

**GitHub Pages**
```bash
git init && git add . && git commit -m "portfolio"
git branch -M main
git remote add origin https://github.com/USERNAME/portfolio.git
git push -u origin main
# then: repo Settings → Pages → Deploy from branch → main / root
```

**Netlify / Cloudflare Pages** — drag the folder into their dashboard, or point
it at the repo. No build command, publish directory is the folder root.

## Notes

- Fonts load from Google Fonts when online, with system fallbacks otherwise.
- Fully responsive, respects `prefers-reduced-motion`, works without JS
  (JS only enhances — content is in the HTML).
