# AEROSTRIDE

A demo e-commerce site for a fictional performance-footwear brand. Flask + SQLite, with plain HTML, CSS and
JavaScript on the front end (no JS libraries, no web fonts, no external requests).

> **Demonstration only.** AEROSTRIDE is fictional. Checkout creates a simulated order record: no payment is
> taken, no card details are requested, nothing ships.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python app.py                  # http://127.0.0.1:5000
```

Tests: `pytest`

## Run with Docker

```bash
docker build -t aerostride .
docker run --rm -p 8000:8000 \
  -e SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  -e INSECURE_COOKIES=1 \
  -v aerostride-data:/data aerostride
```

`INSECURE_COOKIES=1` is only for trying the container over plain `http://localhost`. Behind HTTPS, leave it
out so session cookies are `Secure`.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `AEROSTRIDE_ENV` | `production` enforces a `SECRET_KEY`, Secure cookies and HSTS | `development` |
| `SECRET_KEY` | Signs sessions / CSRF tokens. **Required in production**, never committed | random per start (dev) |
| `AEROSTRIDE_DB` | SQLite path | `instance/aerostride.db` |
| `SITE_URL` | Base for canonical, Open Graph, sitemap URLs | `https://www.aerostride.example` |

## Layout

```
app.py          routes, validation, SQLite, security headers
catalog.py      product + review data (synced into SQLite on start)
templates/      Jinja pages; _ui.html holds reusable macros
static/         css/style.css, js/app.js, images/ (SVG artwork)
tools/          make_art.py regenerates the artwork, make_og.py renders og.png
tests/          pytest suite
```

## How it works

- **Catalogue** lives in `catalog.py` and is upserted into SQLite at startup. Edit prices or copy there.
- **Cart and wishlist** live in `localStorage`. At checkout the cart is sent as `[{id, size, qty}]` and the
  server **re-prices every line from the database**; client-side prices are never trusted.
- **Security:** CSRF token on every POST, server-side validation of all fields, parameterised SQL (user text
  only ever travels as bound parameters; `ORDER BY` comes from a whitelist), strict CSP (no inline script/style),
  `HttpOnly` + `SameSite=Lax` session cookies, order pages visible only to the buyer's session.
- **Performance:** vector artwork (a few KB each), explicit image dimensions to prevent layout shift, lazy
  loading below the fold, `fetchpriority` on the hero, system font stack, cache-busted long-lived static files.
- **SEO:** unique titles/descriptions, canonical + Open Graph tags, Product JSON-LD, `sitemap.xml`, `robots.txt`.

## Before going anywhere real

- The artwork is original procedural SVG, not photography. Drop real WebP/AVIF files into `static/images/`
  and update the template `src` paths.
- Social links point at the platforms' home pages; replace them with real brand profiles.
- Reviews are clearly labelled illustrative. Don't present fictional reviews as real ones.
- Add rate limiting (e.g. at your reverse proxy) for the form endpoints, and real payments only through a
  PCI-compliant hosted provider.
