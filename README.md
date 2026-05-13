# FLOAT — project page (`docs/`)

This folder is served at <https://joao97ribeiro.github.io/FLOAT/> via GitHub Pages.

## Enabling the page

In **Settings → Pages**, choose:

- **Source:** Deploy from a branch
- **Branch:** `float-stable`
- **Folder:** `/docs`

The site is a single `index.html` with Bulma + Plotly loaded from CDN. No build step.

## Updating the interactive plots

The plots under "Interactive Results" read pre-extracted JSON files in
[`static/data/`](./static/data). Regenerate them after a fresh run of
[`examples/08_float_paper_workflow/run.py`](../examples/08_float_paper_workflow):

```bash
python docs/scripts/build_data.py
```

(Or re-run the snippets that ship in [`scripts/build_data.py`](./scripts/build_data.py).)
