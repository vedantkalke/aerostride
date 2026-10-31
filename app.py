"""AEROSTRIDE - demo e-commerce storefront (Flask + SQLite).

AEROSTRIDE is a fictional brand. Checkout is a DEMONSTRATION: no payment is taken
and no card data is requested.

Run locally:   python app.py            (or: flask --app app run)
Production:    gunicorn 'app:create_app()'   with SECRET_KEY set (see README.md)
"""
from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import (Flask, Response, abort, current_app, flash, g, jsonify, redirect,
                   render_template, request, session, url_for)
from werkzeug.exceptions import HTTPException

import catalog

BASE_DIR = Path(__file__).resolve().parent

FREE_SHIPPING = 7999      # INR; orders at/above this ship free
FLAT_SHIPPING = 249       # INR; flat fee below the threshold
MAX_QTY = 10              # per line
MAX_LINES = 20            # lines per order

SORTS = {                 # whitelisted ORDER BY fragments, never built from user input
    "featured": "sort_order ASC",
    "price_asc": "price ASC, sort_order ASC",
    "price_desc": "price DESC, sort_order ASC",
}
CONTACT_TOPICS = ["General enquiry", "Order help", "Sizing and fit",
                  "Returns and exchanges", "Press and partnerships"]
SOCIAL_LINKS = [  # point at the platforms; swap for real brand profiles when they exist
    ("Instagram", "https://www.instagram.com/"),
    ("YouTube", "https://www.youtube.com/"),
    ("X", "https://x.com/"),
    ("Strava", "https://www.strava.com/"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price INTEGER NOT NULL CHECK (price > 0),
    tagline TEXT NOT NULL,
    description TEXT NOT NULL,
    sizes TEXT NOT NULL,
    features TEXT NOT NULL,
    featured INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    pin TEXT NOT NULL,
    subtotal INTEGER NOT NULL,
    shipping INTEGER NOT NULL,
    total INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    product_name TEXT NOT NULL,
    size INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    topic TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

UPSERT_PRODUCT = """
INSERT INTO products (slug, name, category, price, tagline, description, sizes, features, featured, sort_order)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(slug) DO UPDATE SET
    name=excluded.name, category=excluded.category, price=excluded.price, tagline=excluded.tagline,
    description=excluded.description, sizes=excluded.sizes, features=excluded.features,
    featured=excluded.featured, sort_order=excluded.sort_order
"""

# ------------------------------------------------------------------- helpers


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def inr(value) -> str:
    """Indian digit grouping: 1234567 -> ₹12,34,567."""
    s = str(int(value))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return "₹" + s


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def hydrate(row: sqlite3.Row) -> dict:
    p = dict(row)
    p["sizes"] = json.loads(p["sizes"])
    p["features"] = json.loads(p["features"])
    p["featured"] = bool(p["featured"])
    p["short_name"] = p["name"].replace("AEROSTRIDE ", "", 1)
    p["images"] = [f"images/products/{p['slug']}-{view}.svg" for view in catalog.GALLERY_VIEWS]
    return p


def init_db(path: str) -> None:
    """Create tables and sync the catalogue into SQLite (idempotent)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.executescript(SCHEMA)
        for order, p in enumerate(catalog.PRODUCTS):
            con.execute(UPSERT_PRODUCT, (
                p["slug"], p["name"], p["category"], p["price"], p["tagline"], p["description"],
                json.dumps(p["sizes"]), json.dumps(p["features"]), int(p.get("featured", 1)), order))
        con.commit()
    finally:
        con.close()


# ---------------------------------------------------------------- validation

EMAIL_RE = re.compile(r"^[^@\s<>]{1,64}@[^@\s<>]+\.[A-Za-z]{2,}$")
NAME_RE = re.compile(r"^[^\W\d_][\w .,'\-]{1,79}$", re.UNICODE)
CITY_RE = re.compile(r"^[^\W\d_][^\W\d_ .,'\-]*(?:[ .,'\-]+[^\W\d_][^\W\d_ .,'\-]*)*[.]?$", re.UNICODE)
PIN_RE = re.compile(r"^[1-9]\d{5}$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean(value, limit: int) -> str:
    return CONTROL_RE.sub("", (value or "").strip())[:limit]


def normalise_phone(raw: str) -> str:
    digits = re.sub(r"[\s\-()]", "", raw or "")
    if len(digits) > 10:
        digits = re.sub(r"^(\+91|0091|91|0)", "", digits)
    return digits


def valid_email(email: str) -> bool:
    return len(email) <= 254 and bool(EMAIL_RE.match(email))


def validate_checkout(v: dict) -> dict:
    errors = {}
    if not NAME_RE.match(v["name"]):
        errors["name"] = "Enter your full name."
    if not valid_email(v["email"]):
        errors["email"] = "Enter a valid email address."
    if not PHONE_RE.match(normalise_phone(v["phone"])):
        errors["phone"] = "Enter a valid 10-digit mobile number."
    if not 8 <= len(v["address"]) <= 200:
        errors["address"] = "Enter your full address (at least 8 characters)."
    if not (2 <= len(v["city"]) <= 60 and CITY_RE.match(v["city"])):
        errors["city"] = "Enter a valid city."
    if not PIN_RE.match(v["pin"]):
        errors["pin"] = "Enter a valid 6-digit PIN code."
    return errors


def resolve_cart(raw: str):
    """Parse the client's cart and re-price it from the database. Returns (lines, error)."""
    try:
        data = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return [], "We couldn't read your bag."
    if not isinstance(data, list) or not data:
        return [], "Your bag is empty."
    if len(data) > MAX_LINES:
        return [], "Your bag has too many items."
    merged: dict[tuple, int] = {}
    for item in data:
        if not isinstance(item, dict):
            return [], "Your bag contains an invalid item."
        slug, size, qty = item.get("id"), item.get("size"), item.get("qty")
        if (not isinstance(slug, str) or not isinstance(size, int) or not isinstance(qty, int)
                or isinstance(size, bool) or isinstance(qty, bool)):
            return [], "Your bag contains an invalid item."
        if not 1 <= qty <= MAX_QTY:
            return [], f"Quantity must be between 1 and {MAX_QTY}."
        key = (slug, size)
        merged[key] = min(merged.get(key, 0) + qty, MAX_QTY)
    db = get_db()
    lines = []
    for (slug, size), qty in merged.items():
        row = db.execute("SELECT * FROM products WHERE slug = ?", (slug,)).fetchone()
        if row is None:
            return [], "An item in your bag is no longer available."
        product = hydrate(row)
        if size not in product["sizes"]:
            return [], f"Size UK {size} isn't available for {product['short_name']}."
        lines.append({"product": product, "size": size, "qty": qty, "unit_price": product["price"]})
    return lines, None


def compute_totals(lines: list) -> dict:
    subtotal = sum(l["unit_price"] * l["qty"] for l in lines)
    shipping = 0 if subtotal == 0 or subtotal >= FREE_SHIPPING else FLAT_SHIPPING
    return {"subtotal": subtotal, "shipping": shipping, "total": subtotal + shipping}


def safe_json_for_script(data) -> str:
    """JSON that is safe inside a <script type="application/json"> element."""
    return (json.dumps(data, separators=(",", ":"))
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


# --------------------------------------------------------------- app factory


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    production = os.environ.get("AEROSTRIDE_ENV", "development") == "production"
    app.config.update(
        DATABASE=os.environ.get("AEROSTRIDE_DB", str(BASE_DIR / "instance" / "aerostride.db")),
        SITE_URL=os.environ.get("SITE_URL", "https://www.aerostride.example").rstrip("/"),
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=production and os.environ.get("INSECURE_COOKIES") != "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=64 * 1024,
        SEND_FILE_MAX_AGE_DEFAULT=timedelta(days=30),  # asset() adds ?v=<mtime> for cache-busting
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"]:
        if production:
            raise RuntimeError("SECRET_KEY must be set when AEROSTRIDE_ENV=production.")
        app.config["SECRET_KEY"] = secrets.token_hex(32)  # dev only: sessions reset on restart
    init_db(app.config["DATABASE"])

    app.jinja_env.filters["inr"] = inr

    # ---------------------------------------------------------------- security
    def csrf_token() -> str:
        token = session.get("_csrf")
        if not token:
            token = session["_csrf"] = secrets.token_urlsafe(32)
        return token

    @app.before_request
    def csrf_protect():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
            expected = session.get("_csrf", "")
            if not expected or not hmac.compare_digest(sent.encode(), expected.encode()):
                abort(400, description="Your session expired. Please reload the page and try again.")

    @app.after_request
    def security_headers(resp: Response):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        if production:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resp

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # -------------------------------------------------------------- templating
    def asset(path: str) -> str:
        try:
            version = int((Path(app.static_folder) / path).stat().st_mtime)
        except OSError:
            version = 0
        return url_for("static", filename=path, v=version)

    def query_products(where: str = "", params: tuple = (), order: str = SORTS["featured"]) -> list:
        # `where`/`order` are code-defined fragments; every user value travels in `params`.
        sql = f"SELECT * FROM products {where} ORDER BY {order}"  # noqa: S608
        return [hydrate(r) for r in get_db().execute(sql, params).fetchall()]

    def catalog_for_js() -> dict:
        return {p["slug"]: {"name": p["name"], "category": p["category"], "price": p["price"],
                            "sizes": p["sizes"], "url": url_for("product", slug=p["slug"]),
                            "image": asset(p["images"][0])} for p in query_products()}

    @app.context_processor
    def inject():
        return dict(
            csrf_token=csrf_token, asset=asset, categories=catalog.CATEGORIES,
            social_links=SOCIAL_LINKS, free_shipping=FREE_SHIPPING, flat_shipping=FLAT_SHIPPING,
            max_qty=MAX_QTY, year=datetime.now().year, site_url=app.config["SITE_URL"],
            canonical_url=app.config["SITE_URL"] + request.path,
        )

    def wants_json() -> bool:
        return request.headers.get("X-Requested-With") == "fetch"

    # ------------------------------------------------------------------- pages
    @app.get("/")
    def index():
        return render_template("index.html", page_id="home",
                               products=query_products("WHERE featured = 1"), reviews=catalog.REVIEWS)

    @app.get("/shop")
    def shop():
        q = clean(request.args.get("q"), 60)
        category = request.args.get("category", "")
        category = category if category in catalog.CATEGORIES else ""
        bands = {b[0]: b for b in catalog.PRICE_BANDS}
        band = request.args.get("price", "")
        band = band if band in bands else ""
        sort = request.args.get("sort", "featured")
        sort = sort if sort in SORTS else "featured"

        clauses, params = [], []
        if q:
            like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            clauses.append("(name LIKE ? ESCAPE '\\' OR category LIKE ? ESCAPE '\\')")
            params += [like, like]
        if category:
            clauses.append("category = ?")
            params.append(category)
        if band:
            _key, _label, lo, hi = bands[band]
            if lo is not None:
                clauses.append("price >= ?")
                params.append(lo)
            if hi is not None:
                clauses.append("price <= ?")
                params.append(hi)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        products = query_products(where, tuple(params), SORTS[sort])
        filtered = bool(q or category or band or sort != "featured")
        return render_template("shop.html", page_id="shop", products=products, q=q, category=category,
                               band=band, sort=sort, filtered=filtered, price_bands=catalog.PRICE_BANDS)

    @app.get("/product/<slug>")
    def product(slug):
        row = get_db().execute("SELECT * FROM products WHERE slug = ?", (slug,)).fetchone()
        if row is None:
            abort(404)
        p = hydrate(row)
        others = query_products("WHERE slug != ?", (slug,))
        related = ([o for o in others if o["category"] == p["category"]]
                   + [o for o in others if o["category"] != p["category"]])[:3]
        site = app.config["SITE_URL"]
        jsonld = {
            "@context": "https://schema.org", "@type": "Product", "name": p["name"],
            "sku": p["slug"], "category": p["category"], "description": p["description"],
            "brand": {"@type": "Brand", "name": "AEROSTRIDE"},
            "image": [site + url_for("static", filename=i) for i in p["images"]],
            "offers": {"@type": "Offer", "priceCurrency": "INR", "price": str(p["price"]),
                       "availability": "https://schema.org/InStock",
                       "url": site + url_for("product", slug=slug)},
        }
        return render_template("product.html", page_id="product", product=p, related=related, jsonld=jsonld)

    @app.get("/cart")
    def cart():
        return render_template("cart.html", page_id="cart", catalog_json=safe_json_for_script(catalog_for_js()))

    @app.get("/wishlist")
    def wishlist():
        return render_template("wishlist.html", page_id="wishlist", products=query_products())

    def render_checkout(values: dict, errors: dict, cart_error: str | None = None, status: int = 200):
        return render_template("checkout.html", page_id="checkout", values=values, errors=errors,
                               cart_error=cart_error,
                               catalog_json=safe_json_for_script(catalog_for_js())), status

    @app.route("/checkout", methods=["GET", "POST"])
    def checkout():
        if request.method == "GET":
            return render_checkout({}, {})
        values = {"name": clean(request.form.get("name"), 80),
                  "email": clean(request.form.get("email"), 254).lower(),
                  "phone": clean(request.form.get("phone"), 20),
                  "address": clean(request.form.get("address"), 200),
                  "city": clean(request.form.get("city"), 60),
                  "pin": clean(request.form.get("pin"), 6)}
        errors = validate_checkout(values)
        lines, cart_error = resolve_cart(request.form.get("cart", ""))
        if errors or cart_error:
            return render_checkout(values, errors, cart_error, 400)

        totals = compute_totals(lines)
        number = "AS-%s-%s" % (datetime.now().strftime("%y%m%d"),
                               "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6)))
        db = get_db()
        cur = db.execute(
            "INSERT INTO orders (number, name, email, phone, address, city, pin, subtotal, shipping, total, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (number, values["name"], values["email"], normalise_phone(values["phone"]), values["address"],
             values["city"], values["pin"], totals["subtotal"], totals["shipping"], totals["total"], now_iso()))
        db.executemany(
            "INSERT INTO order_items (order_id, product_id, product_name, size, quantity, unit_price) VALUES (?, ?, ?, ?, ?, ?)",
            [(cur.lastrowid, l["product"]["id"], l["product"]["name"], l["size"], l["qty"], l["unit_price"])
             for l in lines])
        db.commit()
        session["last_order"] = number
        return redirect(url_for("order_success", number=number), 303)

    @app.get("/order/<number>")
    def order_success(number):
        if session.get("last_order") != number:  # order pages are only shown to the buyer's session
            abort(404)
        db = get_db()
        order = db.execute("SELECT * FROM orders WHERE number = ?", (number,)).fetchone()
        if order is None:
            abort(404)
        items = db.execute("SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order["id"],)).fetchall()
        return render_template("success.html", page_id="success", order=order, items=items)

    @app.get("/about")
    def about():
        return render_template("about.html", page_id="about")

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "GET":
            return render_template("contact.html", page_id="contact", values={}, errors={})
        values = {"name": clean(request.form.get("name"), 80),
                  "email": clean(request.form.get("email"), 254).lower(),
                  "subject": request.form.get("subject", ""),
                  "message": clean(request.form.get("message"), 2000)}
        errors = {}
        if not NAME_RE.match(values["name"]):
            errors["name"] = "Enter your name."
        if not valid_email(values["email"]):
            errors["email"] = "Enter a valid email address."
        if values["subject"] not in CONTACT_TOPICS:
            values["subject"] = CONTACT_TOPICS[0]
        if len(values["message"]) < 10:
            errors["message"] = "Your message should be at least 10 characters."
        if errors:
            return render_template("contact.html", page_id="contact", values=values, errors=errors), 400
        db = get_db()
        db.execute("INSERT INTO messages (name, email, topic, message, created_at) VALUES (?, ?, ?, ?, ?)",
                   (values["name"], values["email"], values["subject"], values["message"], now_iso()))
        db.commit()
        flash("Thanks! Your message has been received. We usually reply within two working days.", "success")
        return redirect(url_for("contact"), 303)

    @app.post("/newsletter")
    def newsletter():
        email = clean(request.form.get("email"), 254).lower()
        if not valid_email(email):
            message = "Please enter a valid email address."
            if wants_json():
                return jsonify(ok=False, message=message), 400
            flash(message, "error")
            return redirect(url_for("index", _anchor="newsletter"), 303)
        db = get_db()
        db.execute("INSERT OR IGNORE INTO subscribers (email, created_at) VALUES (?, ?)", (email, now_iso()))
        db.commit()
        message = "You're in! Look out for our next drop."
        if wants_json():
            return jsonify(ok=True, message=message)
        flash(message, "success")
        return redirect(url_for("index", _anchor="newsletter"), 303)

    @app.get("/privacy")
    def privacy():
        return render_template("privacy.html", page_id="privacy")

    @app.get("/terms")
    def terms():
        return render_template("terms.html", page_id="terms")

    @app.get("/healthz")
    def healthz():
        get_db().execute("SELECT 1")
        return jsonify(status="ok")

    @app.get("/robots.txt")
    def robots():
        return Response("User-agent: *\nAllow: /\nDisallow: /cart\nDisallow: /checkout\nDisallow: /order/\n"
                        f"Sitemap: {app.config['SITE_URL']}/sitemap.xml\n", mimetype="text/plain")

    @app.get("/sitemap.xml")
    def sitemap():
        paths = [url_for(e) for e in ("index", "shop", "about", "contact", "privacy", "terms")]
        paths += [url_for("product", slug=p["slug"]) for p in query_products()]
        base = app.config["SITE_URL"]
        body = "".join(f"  <url><loc>{base}{p}</loc></url>\n" for p in paths)
        return Response('<?xml version="1.0" encoding="UTF-8"?>\n'
                        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n",
                        mimetype="application/xml")

    # ------------------------------------------------------------------ errors
    def error_response(code: int, title: str, text: str):
        if wants_json():
            return jsonify(ok=False, message=text), code
        return render_template("error.html", page_id="error", code=code, title=title, text=text), code

    @app.errorhandler(HTTPException)
    def http_error(err: HTTPException):
        if err.code == 404:
            return error_response(404, "Page not found", "That page has moved or never existed.")
        if err.code in (400, 413):
            return error_response(err.code, "Request problem", err.description)
        if err.code == 405:
            return error_response(405, "Not allowed", "That action isn't available here.")
        return error_response(err.code or 500, "Something went wrong", "Please try again in a moment.")

    @app.errorhandler(Exception)
    def server_error(err):
        current_app.logger.exception("Unhandled error: %s", err)
        return error_response(500, "Something went wrong", "Please try again in a moment.")

    return app


if __name__ == "__main__":
    create_app().run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")),
                     debug=os.environ.get("FLASK_DEBUG") == "1")
