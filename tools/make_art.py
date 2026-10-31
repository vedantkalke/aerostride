"""Generate AEROSTRIDE's original vector artwork (shoes, hero, campaign, story).

Run from the project root:  python tools/make_art.py

All artwork is original and procedurally drawn, so there are no third-party
assets to license. SVG keeps every image tiny (a few KB), sharp at any size and
cheap to cache. Replace any file in static/images with real photography
(WebP/AVIF) and keep the same file name or update the templates.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import catalog  # noqa: E402

OUT = ROOT / "static" / "images"
PRODUCTS_OUT = OUT / "products"
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"

ORANGE, INK, PAPER, STONE = "#FF5722", "#111111", "#F7F7F5", "#EAEAE7"

UPPER = (
    "M114 400 C104 350 108 290 130 244 C160 228 200 240 232 262 L256 216 "
    "C262 208 276 208 284 216 C340 280 440 340 520 372 C590 396 660 396 712 416 "
    "C730 424 730 440 712 446 L114 446 Z"
)

# Midsole outlines: (path, bottom-edge path used for the outsole stroke)
MIDSOLES = {
    "thick": (
        "M112 392 C300 410 520 424 712 430 C728 432 730 446 716 456 C690 474 640 476 600 478 "
        "C450 484 250 484 150 478 C118 474 100 446 106 420 Z",
        "M150 478 C250 484 450 484 600 478 C640 476 690 474 716 456",
    ),
    "flat": (
        "M112 396 C300 408 520 422 712 430 C728 432 730 446 716 456 C700 470 650 472 600 472 "
        "C450 474 250 474 150 472 C118 470 104 448 106 424 Z",
        "M150 472 C250 474 450 474 600 472 C650 472 700 470 716 456",
    ),
}


def shoe_group(p: dict, uid: str = "s") -> str:
    """Return the <g> markup for one side-profile shoe (design space 800x600)."""
    style = p["style"]
    upper, accent, sole = p["upper"], p["accent"], p["sole"]
    midsole_d, bottom_d = MIDSOLES["thick" if style in ("racer", "trail") else "flat"]
    dark = "#111111"
    is_dark_upper = upper.lower() in ("#1b1b1b", "#111111")
    lace = "#F7F7F5" if is_dark_upper or style == "trail" else "#FFFFFF"
    if upper.lower() == "#f7f7f5":
        lace = "#B9B6AE"  # light upper: darker laces so they stay visible
    parts = [
        f'<defs><clipPath id="{uid}u"><path d="{UPPER}"/></clipPath>'
        f'<clipPath id="{uid}m"><path d="{midsole_d}"/></clipPath>'
        f'<pattern id="{uid}p" width="9" height="9" patternUnits="userSpaceOnUse">'
        f'<circle cx="2.5" cy="2.5" r="1.3" fill="#fff" opacity=".32"/></pattern></defs>'
    ]
    # upper + textures (clipped to upper silhouette)
    parts.append(f'<path d="{UPPER}" fill="{upper}"/>')
    parts.append(f'<g clip-path="url(#{uid}u)">')
    if style in ("racer", "trainer", "trail"):
        parts.append(f'<rect x="100" y="200" width="650" height="260" fill="url(#{uid}p)"/>')
    # swooping side panel
    parts.append(
        f'<path d="M110 392 C190 384 290 360 372 318 C402 303 436 306 458 326 '
        f'C390 392 280 426 110 424 Z" fill="{accent}"/>'
    )
    # toe cap
    toe_op = ".22" if style != "trail" else ".35"
    parts.append(f'<path d="M590 392 C640 396 700 404 730 420 L730 450 L600 450 C612 430 608 408 590 392 Z" '
                 f'fill="{dark}" opacity="{toe_op}"/>')
    # heel counter shade
    parts.append(f'<path d="M100 250 C150 250 170 300 168 440 L100 440 Z" fill="{dark}" opacity=".14"/>')
    if style == "lifestyle":
        parts.append(f'<path d="M330 396 C420 400 520 404 600 410 L640 440 L330 440 Z" fill="{dark}" opacity=".10"/>')
    if style == "trainer":
        for x in (380, 430, 480):
            parts.append(f'<path d="M{x} 352 L{x + 36} 410" stroke="{accent}" stroke-width="9" stroke-linecap="round" opacity=".9"/>')
    parts.append("</g>")
    # collar padding + tongue
    parts.append(
        f'<path d="M130 244 C160 228 200 240 232 262 L222 290 C190 270 156 262 126 278 Z" '
        f'fill="{dark}" opacity=".28"/>'
    )
    parts.append(f'<path d="M232 262 L256 216 C262 208 276 208 284 216 L300 236 L246 276 Z" fill="#fff" opacity=".22"/>')
    # heel pull tab
    parts.append(f'<path d="M122 262 C116 240 118 222 128 210 L146 214 C140 228 140 244 146 258 Z" fill="{accent}"/>')
    # laces
    sx, sy, ex, ey = 276, 242, 494, 362
    for i in range(6):
        t = i / 5
        cx, cy = sx + (ex - sx) * t, sy + (ey - sy) * t
        parts.append(
            f'<path d="M{cx - 15:.0f} {cy + 12:.0f} L{cx + 17:.0f} {cy - 14:.0f}" stroke="{lace}" '
            f'stroke-width="8" stroke-linecap="round"/>'
        )
    # brand mark (original chevron)
    parts.append(f'<path d="M170 346 l20 -34 l20 34" fill="none" stroke="{lace}" stroke-width="6" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')
    # midsole
    parts.append(f'<path d="{midsole_d}" fill="{sole}"/>')
    parts.append(f'<g clip-path="url(#{uid}m)">')
    line_c = dark
    parts.append(f'<path d="M110 436 C300 450 520 456 716 446" fill="none" stroke="{line_c}" stroke-width="3" opacity=".16"/>')
    if style == "racer":
        parts.append(f'<path d="M120 440 C300 452 520 458 716 448" fill="none" stroke="{dark}" stroke-width="7" opacity=".85"/>')
        parts.append(f'<path d="M110 412 C300 428 520 436 716 436" fill="none" stroke="{accent}" stroke-width="5" opacity=".9"/>')
    elif style == "lifestyle":
        parts.append(f'<path d="M122 420 C300 430 520 438 704 440" fill="none" stroke="{dark}" stroke-width="2" '
                     f'stroke-dasharray="7 6" opacity=".35"/>')
    elif style == "trainer":
        parts.append(f'<path d="M110 424 C300 436 520 442 716 440" fill="none" stroke="{accent}" stroke-width="5"/>')
    elif style == "trail":
        parts.append(f'<path d="M110 424 C300 436 520 442 716 440" fill="none" stroke="{accent}" stroke-width="4" opacity=".9"/>')
    # outsole strip
    parts.append(f'<path d="{bottom_d}" fill="none" stroke="{dark}" stroke-width="16" stroke-linecap="round"/>')
    parts.append("</g>")
    # trail lugs
    if style == "trail":
        for i in range(17):
            x = 150 + i * 33
            y = 480 + (1 if i < 14 else -(i - 13) * 3)
            parts.append(f'<path d="M{x} {y - 4} h20 l-4 14 h-12 Z" fill="{dark}"/>')
    return "".join(parts)


def shoe_svg_wrap(inner: str, view: str, bg: str, extra: str = "", dark_bg: bool = False) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="800" height="600" '
        f'role="img" aria-hidden="true"><rect width="800" height="600" fill="{bg}"/>{extra}{inner}</svg>'
    )


def view_side(p: dict, slug: str) -> str:
    pal = p
    shadow = '<ellipse cx="400" cy="520" rx="330" ry="15" fill="#111" opacity=".10"/>'
    shoe = f'<g transform="translate(400 296) scale(1.1) translate(-415 -345)">{shoe_group(pal, "a")}</g>'
    return shoe_svg_wrap(shadow + shoe, "side", pal["bg"])


def view_angle(p: dict, slug: str) -> str:
    ring = (f'<circle cx="400" cy="300" r="250" fill="none" stroke="{ORANGE}" stroke-width="3" opacity=".9"/>'
            f'<circle cx="400" cy="300" r="190" fill="{ORANGE}" opacity=".12"/>')
    shoe = f'<g transform="translate(400 300) rotate(-9) scale(1.08) translate(-415 -345)">{shoe_group(p, "b")}</g>'
    return shoe_svg_wrap(ring + shoe, "angle", INK)


def view_detail(p: dict, slug: str) -> str:
    shoe = f'<g transform="translate(40 10) scale(2.1) translate(-100 -230)">{shoe_group(p, "c")}</g>'

    def tag(x, y, w, text):
        return (
            f'<rect x="{x}" y="{y}" width="{w}" height="38" rx="19" fill="#fff"/>'
            f'<text x="{x + w / 2}" y="{y + 25}" text-anchor="middle" font-family="{FONT}" font-weight="800" '
            f'font-size="15" letter-spacing="2.5" fill="{INK}">{text}</text>'
        )

    callouts = (
        f'<g stroke="{INK}" stroke-width="2" fill="none">'
        f'<path d="M296 196 L520 120"/><path d="M470 478 L600 478 L600 540"/></g>'
        f'<circle cx="296" cy="196" r="9" fill="{ORANGE}"/><circle cx="470" cy="478" r="9" fill="{ORANGE}"/>'
        + tag(500, 84, 232, "ENGINEERED UPPER")
        + tag(500, 540, 150, "MIDSOLE")
    )
    return shoe_svg_wrap(shoe + callouts, "detail", STONE)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_products() -> None:
    for p in catalog.PRODUCTS:
        slug, pal = p["slug"], p["palette"]
        write(PRODUCTS_OUT / f"{slug}-side.svg", view_side(pal, slug))
        write(PRODUCTS_OUT / f"{slug}-angle.svg", view_angle(pal, slug))
        write(PRODUCTS_OUT / f"{slug}-detail.svg", view_detail(pal, slug))


# --------------------------------------------------------------------------
# Hero, campaign, story, brand
# --------------------------------------------------------------------------
def make_hero() -> None:
    pal = catalog.PRODUCTS[0]["palette"]
    lines = "".join(
        f'<path d="M{20 + (i * 37) % 120} {170 + i * 52} H{210 + (i * 53) % 160}" stroke="{INK}" '
        f'stroke-width="5" stroke-linecap="round" opacity=".12"/>'
        for i in range(8)
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 760" width="1000" height="760" role="img" aria-hidden="true">'
        f'<circle cx="540" cy="360" r="320" fill="{ORANGE}"/>{lines}'
        f'<ellipse cx="560" cy="650" rx="360" ry="18" fill="#111" opacity=".16"/>'
        f'<g transform="translate(520 380) rotate(-10) scale(1.2) translate(-415 -345)">{shoe_group(pal, "h")}</g></svg>'
    )
    write(OUT / "hero.svg", svg)


def scene_wrap(inner: str, shoe_pal: dict, label: str, bg: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 750" width="600" height="750" role="img" aria-hidden="true">'
        f'<rect width="600" height="750" fill="{bg}"/>{inner}'
        f'<g transform="translate(300 590) rotate(-6) scale(.62) translate(-415 -330)">{shoe_group(shoe_pal, "z")}</g>'
        f'<rect x="24" y="684" width="{len(label) * 20 + 40}" height="46" rx="23" fill="#111"/>'
        f'<text x="44" y="715" font-family="{FONT}" font-weight="800" font-size="20" letter-spacing="5" fill="#fff">{label}</text></svg>'
    )


def make_campaign() -> None:
    # TRACK - converging lanes
    lanes = [f'<polygon points="0,750 600,750 600,330 0,330" fill="{ORANGE}"/>']
    for i in range(-5, 6):
        x_far = 300 + i * 26
        x_near = 300 + i * 190
        lanes.append(f'<polygon points="{x_far - 2},330 {x_far + 2},330 {x_near + 6},750 {x_near - 6},750" fill="#fff" opacity=".85"/>')
    track = (
        f'<rect width="600" height="330" fill="{INK}"/>'
        f'<circle cx="300" cy="330" r="120" fill="{ORANGE}" opacity=".35"/>' + "".join(lanes) +
        f'<rect y="330" width="600" height="6" fill="{INK}"/>'
    )
    write(OUT / "campaign-track.svg", scene_wrap(track, catalog.PRODUCTS[1]["palette"], "TRACK", INK))
    # CITY - blocks + sun
    blocks = "".join(
        f'<rect x="{x}" y="{y}" width="{w}" height="{750 - y}" fill="{c}"/>'
        for x, y, w, c in [(0, 300, 110, "#2B2B2B"), (96, 220, 90, INK), (170, 340, 120, "#333"), (276, 180, 80, INK),
                           (340, 290, 130, "#2B2B2B"), (456, 240, 80, INK), (520, 330, 100, "#333")]
    )
    windows = "".join(
        f'<rect x="{x}" y="{y}" width="8" height="12" fill="#fff" opacity=".35"/>'
        for x in range(112, 170, 20) for y in range(250, 420, 36)
    )
    city = f'<rect width="600" height="750" fill="{STONE}"/><circle cx="430" cy="170" r="84" fill="{ORANGE}"/>{blocks}{windows}'
    write(OUT / "campaign-city.svg", scene_wrap(city, catalog.PRODUCTS[4]["palette"], "CITY", "#2B2B2B"))
    # TRAIL - layered ridges
    ridges = (
        f'<rect width="600" height="750" fill="{STONE}"/><circle cx="170" cy="170" r="70" fill="{ORANGE}"/>'
        f'<polygon points="0,420 120,300 220,380 340,230 460,360 600,280 600,750 0,750" fill="#6F8F6B"/>'
        f'<polygon points="0,500 140,390 260,470 380,340 520,450 600,400 600,750 0,750" fill="#3E5A3C"/>'
        f'<polygon points="0,590 160,500 300,570 440,480 600,560 600,750 0,750" fill="#22351F"/>'
    )
    write(OUT / "campaign-trail.svg", scene_wrap(ridges, catalog.PRODUCTS[2]["palette"], "TRAIL", "#22351F"))


def make_story() -> None:
    """Exploded layer view of a shoe: a brand-story illustration."""
    pal = catalog.PRODUCTS[2]["palette"]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 900" width="800" height="900" role="img" aria-hidden="true">'
        f'<rect width="800" height="900" fill="{INK}"/>'
        f'<circle cx="400" cy="420" r="300" fill="none" stroke="{ORANGE}" stroke-width="3"/>'
        f'<circle cx="400" cy="420" r="230" fill="{ORANGE}" opacity=".14"/>'
        f'<g transform="translate(400 430) rotate(-8) scale(.95) translate(-415 -335)">{shoe_group(pal, "t")}</g>'
        f'<g font-family="{FONT}" font-weight="800" fill="#fff" font-size="20" letter-spacing="5">'
        f'<text x="48" y="96">COMFORT</text><text x="752" y="96" text-anchor="end">MOVEMENT</text>'
        f'<text x="48" y="840">PERFORMANCE</text><text x="752" y="840" text-anchor="end">INNOVATION</text></g></svg>'
    )
    write(OUT / "story.svg", svg)


def make_brand() -> None:
    write(
        OUT / "favicon.svg",
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="{INK}"/>'
        f'<path d="M14 46 L32 14 L50 46" fill="none" stroke="{ORANGE}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<path d="M22 46 H42" stroke="#fff" stroke-width="5" stroke-linecap="round"/></svg>',
    )
    # Open Graph needs a raster image; this SVG is rasterised by tools/make_og.py
    pal = catalog.PRODUCTS[0]["palette"]
    write(
        OUT / "og-source.svg",
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">'
        f'<rect width="1200" height="630" fill="{STONE}"/><circle cx="900" cy="315" r="255" fill="{ORANGE}"/>'
        f'<g transform="translate(890 340) rotate(-10) scale(.9) translate(-415 -345)">{shoe_group(pal, "o")}</g>'
        f'<g font-family="{FONT}" font-weight="900" fill="{INK}">'
        f'<text x="70" y="250" font-size="76" letter-spacing="-1">AEROSTRIDE</text>'
        f'<text x="70" y="318" font-size="22" letter-spacing="4">ENGINEERED FOR EVERY STRIDE.</text></g></svg>',
    )


if __name__ == "__main__":
    make_products()
    make_hero()
    make_campaign()
    make_story()
    make_brand()
    print("Artwork written to", OUT)
