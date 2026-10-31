import json
import re
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as aerostride  # noqa: E402

GOOD = {"name": "Asha Verma", "email": "asha@example.com", "phone": "98765 43210",
        "address": "12 MG Road, Camp", "city": "Pune", "pin": "411001"}


@pytest.fixture()
def client(tmp_path):
    app = aerostride.create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(tmp_path / "t.db")})
    c = app.test_client()
    c.db_path = app.config["DATABASE"]
    return c


def token(client):
    client.get("/")
    with client.session_transaction() as s:
        return s["_csrf"]


def checkout(client, cart, **overrides):
    data = {**GOOD, **overrides, "csrf_token": token(client), "cart": json.dumps(cart)}
    return client.post("/checkout", data=data)


def rows(client, sql):
    con = sqlite3.connect(client.db_path)
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


@pytest.mark.parametrize("url", ["/", "/shop", "/product/velocity-x", "/cart", "/checkout", "/wishlist",
                                 "/about", "/contact", "/privacy", "/terms", "/healthz", "/robots.txt",
                                 "/sitemap.xml"])
def test_pages_render(client, url):
    assert client.get(url).status_code == 200


def test_unknown_routes_404(client):
    assert client.get("/product/nope").status_code == 404
    assert client.get("/order/AS-000000-AAAAAA").status_code == 404


def test_home_has_six_featured_products_and_seo(client):
    html = client.get("/").get_data(as_text=True)
    assert html.count('class="card"') == 6
    assert "<title>" in html and 'rel="canonical"' in html and 'property="og:image"' in html
    assert "RUN" in html and "BEYOND" in html and "STAY AHEAD OF THE CURVE." in html


def test_shop_search_filter_sort(client):
    def names(qs):
        html = client.get("/shop" + qs).get_data(as_text=True)
        return re.findall(r'class="card-title"><a [^>]*>([^<]+)</a>', html)

    assert len(names("")) == 8
    assert names("?q=velocity") == ["AEROSTRIDE VELOCITY X"]
    assert names("?q=zzzz") == []
    assert names("?q=%25") == []  # LIKE wildcards are escaped
    assert set(names("?category=Trail")) == {"AEROSTRIDE TRAIL EDGE", "AEROSTRIDE SUMMIT RIDGE"}
    assert names("?category=Bogus") == names("")
    assert all(n in names("") for n in names("?price=over-10000"))
    def prices(qs):
        html = client.get("/shop" + qs).get_data(as_text=True)
        return [int(p.replace(",", "")) for p in re.findall(r'card-price">₹([\d,]+)<', html)]

    assert prices("?sort=price_asc") == sorted(prices("?sort=price_asc"))
    assert prices("?sort=price_desc") == sorted(prices("?sort=price_desc"), reverse=True)


def test_price_filter_bounds(client):
    html = client.get("/shop?price=under-5000").get_data(as_text=True)
    prices = [int(p.replace(",", "")) for p in re.findall(r'card-price">₹([\d,]+)<', html)]
    assert prices and all(p <= 4999 for p in prices)


def test_product_page_has_structured_data(client):
    html = client.get("/product/nexus-pro").get_data(as_text=True)
    ld = json.loads(re.search(r'application/ld\+json">(.*?)</script>', html, re.S).group(1))
    assert ld["@type"] == "Product" and ld["offers"]["priceCurrency"] == "INR"


def test_csrf_required(client):
    assert client.post("/newsletter", data={"email": "a@b.co"}).status_code == 400
    assert client.post("/checkout", data={}).status_code == 400
    assert client.post("/contact", data={}).status_code == 400


def test_newsletter(client):
    t = token(client)
    bad = client.post("/newsletter", data={"email": "nope", "csrf_token": t}, headers={"X-Requested-With": "fetch"})
    assert bad.status_code == 400 and bad.get_json()["ok"] is False
    ok = client.post("/newsletter", data={"email": "Fan@Example.com"}, headers={"X-Requested-With": "fetch", "X-CSRF-Token": t})
    assert ok.status_code == 200 and ok.get_json()["ok"] is True
    client.post("/newsletter", data={"email": "fan@example.com", "csrf_token": t})  # duplicate is harmless
    assert rows(client, "SELECT email FROM subscribers") == [("fan@example.com",)]


def test_contact_form(client):
    t = token(client)
    bad = client.post("/contact", data={"csrf_token": t, "name": "", "email": "x", "message": "hi"})
    assert bad.status_code == 400 and "Enter your name" in bad.get_data(as_text=True)
    ok = client.post("/contact", data={"csrf_token": t, "name": "Ravi", "email": "r@x.in",
                                       "subject": "Order help", "message": "Where is my order please?"})
    assert ok.status_code == 303
    assert rows(client, "SELECT topic FROM messages") == [("Order help",)]


def test_checkout_happy_path_reprices_server_side(client):
    cart = [{"id": "halo-lite", "size": 8, "qty": 2}, {"id": "pulse-2", "size": 9, "qty": 1}]
    resp = checkout(client, cart)
    assert resp.status_code == 303
    page = client.get(resp.headers["Location"])
    assert page.status_code == 200 and "simulated" in page.get_data(as_text=True)
    total, shipping, subtotal = rows(client, "SELECT total, shipping, subtotal FROM orders")[0]
    assert subtotal == total - shipping and shipping in (0, aerostride.FLAT_SHIPPING)
    assert rows(client, "SELECT COUNT(*), SUM(quantity) FROM order_items") == [(2, 3)]


def test_shipping_threshold(client):
    low = [{"id": "halo-lite", "size": 6, "qty": 1}]
    high = [{"id": "velocity-x", "size": 6, "qty": 1}]
    checkout(client, low)
    checkout(client, high)
    ship = [r[0] for r in rows(client, "SELECT shipping FROM orders ORDER BY id")]
    assert ship == [aerostride.FLAT_SHIPPING, 0]


def test_order_page_only_visible_to_buyer(client):
    resp = checkout(client, [{"id": "halo-lite", "size": 8, "qty": 1}])
    url = resp.headers["Location"]
    other = client.application.test_client()
    assert other.get(url).status_code == 404


@pytest.mark.parametrize("field,value", [("name", "A"), ("name", "<script>"), ("email", "bad@"),
                                         ("phone", "12345"), ("phone", "5123456789"), ("address", "short"),
                                         ("city", "P1"), ("pin", "012345"), ("pin", "4110")])
def test_checkout_server_validation(client, field, value):
    resp = checkout(client, [{"id": "halo-lite", "size": 8, "qty": 1}], **{field: value})
    assert resp.status_code == 400
    assert rows(client, "SELECT COUNT(*) FROM orders") == [(0,)]


@pytest.mark.parametrize("cart", [
    [], "garbage", [{"id": "nope", "size": 8, "qty": 1}], [{"id": "halo-lite", "size": 5, "qty": 1}],
    [{"id": "halo-lite", "size": 8, "qty": 0}], [{"id": "halo-lite", "size": 8, "qty": 99}],
    [{"id": "halo-lite", "size": "8", "qty": 1}], [{"id": "halo-lite", "size": True, "qty": 1}],
    ["x"], [{"id": "halo-lite", "size": 8, "qty": 1, "price": 1}] * 40,
])
def test_checkout_rejects_bad_carts(client, cart):
    data = {**GOOD, "csrf_token": token(client), "cart": cart if isinstance(cart, str) else json.dumps(cart)}
    resp = client.post("/checkout", data=data)
    assert resp.status_code == 400
    assert rows(client, "SELECT COUNT(*) FROM orders") == [(0,)]


def test_client_price_is_ignored(client):
    checkout(client, [{"id": "velocity-x", "size": 8, "qty": 1, "price": 1}])
    assert rows(client, "SELECT subtotal FROM orders") == [(12999,)]


def test_errors_keep_entered_values_and_escape(client):
    resp = checkout(client, [{"id": "halo-lite", "size": 8, "qty": 1}], name='"><img src=x onerror=alert(1)>')
    html = resp.get_data(as_text=True)
    assert resp.status_code == 400 and "<img src=x" not in html


def test_security_headers(client):
    h = client.get("/").headers
    assert "default-src 'self'" in h["Content-Security-Policy"]
    assert h["X-Content-Type-Options"] == "nosniff" and h["X-Frame-Options"] == "DENY"


def test_inr_formatting():
    assert [aerostride.inr(n) for n in (999, 3999, 12999, 1234567)] == ["₹999", "₹3,999", "₹12,999", "₹12,34,567"]


def test_production_requires_secret_key(monkeypatch, tmp_path):
    monkeypatch.setenv("AEROSTRIDE_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        aerostride.create_app({"DATABASE": str(tmp_path / "p.db")})
