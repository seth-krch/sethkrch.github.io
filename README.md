# sethkrch.com

Personal site for Seth Krch, freelance automation developer. Served by GitHub
Pages from the root of `main`, with the custom domain set in `CNAME`.

The whole site is one static file, `index.html`, with no build step:

- **Styles** are inline in the `<style>` block. Colors and fonts are tokens on
  `:root` at the top.
- **The gravity-well hero** is drawn with Three.js r128, loaded from cdnjs.
- **The small wireframes** on the cards are drawn on 2D canvases. The shape
  each one draws comes from its `data-shape` attribute.
- **The step animations** on the billing pipeline and the Method section are
  driven by the sequencer near the end of the script.

All motion stops when the visitor's system has reduced motion turned on.

## Preview locally

```bash
python3 -m http.server 8000
# open http://127.0.0.1:8000
```
