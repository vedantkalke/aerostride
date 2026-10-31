"""Static catalogue data for AEROSTRIDE (fictional brand, fictional products).

Kept separate from app.py so product data can be edited without touching
routing code. The database is seeded from this module on first run.
"""

CATEGORIES = ["Running", "Training", "Lifestyle", "Trail"]

PRICE_BANDS = [
    ("", "Any price", None, None),
    ("under-5000", "Under ₹5,000", 0, 4999),
    ("5000-8000", "₹5,000 – ₹8,000", 5000, 8000),
    ("8000-10000", "₹8,000 – ₹10,000", 8001, 10000),
    ("over-10000", "Over ₹10,000", 10001, None),
]

DEFAULT_SIZES = [6, 7, 8, 9, 10, 11]

# palette keys are consumed by tools/make_art.py to draw the artwork.
PRODUCTS = [
    {
        "slug": "velocity-x",
        "name": "AEROSTRIDE VELOCITY X",
        "category": "Running",
        "price": 12999,
        "sizes": [6, 7, 8, 9, 10, 11],
        "tagline": "Race-day speed, carbon-plated.",
        "description": (
            "Our fastest road racer. A full-length carbon plate sits inside a "
            "responsive foam stack to return energy with every toe-off, while a "
            "featherweight engineered mesh keeps the upper breathable at pace."
        ),
        "features": [
            "Full-length carbon propulsion plate",
            "High-rebound AeroFoam midsole, 38 mm heel stack",
            "Engineered air-mesh upper, 198 g (UK 8)",
            "6 mm heel-to-toe drop",
        ],
        "palette": {"upper": "#FF5722", "accent": "#111111", "sole": "#FFFFFF", "bg": "#EAEAE7", "style": "racer"},
        "featured": 1,
    },
    {
        "slug": "nexus-pro",
        "name": "AEROSTRIDE NEXUS PRO",
        "category": "Training",
        "price": 8999,
        "sizes": [6, 7, 8, 9, 10, 11],
        "tagline": "Stable under load, quick on the turn.",
        "description": (
            "Built for gym floors and HIIT circuits. A wide, flat platform gives "
            "stable footing for lifts, while a flexible forefoot and reinforced "
            "sidewalls hold up through lateral drills and rope climbs."
        ),
        "features": [
            "Wide stability platform with firm heel counter",
            "Flex-groove forefoot for jumps and sprints",
            "Abrasion-resistant wrap on high-wear zones",
            "8 mm heel-to-toe drop",
        ],
        "palette": {"upper": "#1B1B1B", "accent": "#FF5722", "sole": "#F7F7F5", "bg": "#EAEAE7", "style": "trainer"},
        "featured": 1,
    },
    {
        "slug": "apex-runner",
        "name": "AEROSTRIDE APEX RUNNER",
        "category": "Running",
        "price": 10499,
        "sizes": [6, 7, 8, 9, 10, 11],
        "tagline": "Daily miles, cushioned and calm.",
        "description": (
            "The everyday trainer for long weekly mileage. A generous cushioning "
            "stack and a smooth rocker geometry keep strides easy from the first "
            "kilometre to the last."
        ),
        "features": [
            "Adaptive dual-density cushioning",
            "Rocker geometry for smooth transitions",
            "Seamless knit upper with padded collar",
            "10 mm heel-to-toe drop",
        ],
        "palette": {"upper": "#2F5BFF", "accent": "#F7F7F5", "sole": "#FF5722", "bg": "#EAEAE7", "style": "racer"},
        "featured": 1,
    },
    {
        "slug": "trail-edge",
        "name": "AEROSTRIDE TRAIL EDGE",
        "category": "Trail",
        "price": 9499,
        "sizes": [6, 7, 8, 9, 10, 11],
        "tagline": "Grip that reads the terrain.",
        "description": (
            "Aggressive multi-directional lugs and a protective rock plate make "
            "this the go-to for loose gravel, wet roots and steep descents, with "
            "a gusseted tongue that keeps debris out."
        ),
        "features": [
            "5 mm multi-directional traction lugs",
            "Underfoot rock plate",
            "Gusseted tongue and toe bumper",
            "Quick-drain mesh upper",
        ],
        "palette": {"upper": "#3E5A3C", "accent": "#FF5722", "sole": "#111111", "bg": "#EAEAE7", "style": "trail"},
        "featured": 1,
    },
    {
        "slug": "pulse-2",
        "name": "AEROSTRIDE PULSE 2.0",
        "category": "Lifestyle",
        "price": 5999,
        "sizes": [6, 7, 8, 9, 10, 11],
        "tagline": "Street-ready, all-day comfort.",
        "description": (
            "A clean, minimal sneaker with running-grade comfort. Soft suede "
            "overlays, a cushioned insole and a low-profile sole make Pulse 2.0 "
            "an easy match for everything in your wardrobe."
        ),
        "features": [
            "Premium suede and mesh upper",
            "Memory-foam cushioned insole",
            "Low-profile cupsole with flex grooves",
            "Minimal tonal branding",
        ],
        "palette": {"upper": "#F7F7F5", "accent": "#FF5722", "sole": "#E2E0DA", "bg": "#EAEAE7", "style": "lifestyle"},
        "featured": 1,
    },
    {
        "slug": "cloud-flex",
        "name": "AEROSTRIDE CLOUD FLEX",
        "category": "Training",
        "price": 3999,
        "sizes": [6, 7, 8, 9, 10, 11],
        "tagline": "Light, soft, and ready for anything.",
        "description": (
            "Our most accessible performance shoe. A soft, lightweight foam "
            "midsole and a stretch-knit upper adapt to your foot for gym "
            "sessions, walks and everyday errands."
        ),
        "features": [
            "Ultra-light CloudFoam midsole",
            "Stretch-knit sock-fit upper",
            "Flexible outsole for natural movement",
            "Machine-washable upper",
        ],
        "palette": {"upper": "#C9D1D8", "accent": "#111111", "sole": "#FFFFFF", "bg": "#EAEAE7", "style": "trainer"},
        "featured": 1,
    },
    {
        "slug": "halo-lite",
        "name": "AEROSTRIDE HALO LITE",
        "category": "Lifestyle",
        "price": 4499,
        "sizes": [6, 7, 8, 9, 10, 11],
        "tagline": "Understated, featherweight, everyday.",
        "description": (
            "A low-key everyday sneaker with a lightweight foam sole and a soft, "
            "breathable upper. Simple lines, rounded toe, endless pairings."
        ),
        "features": [
            "Breathable recycled-poly upper",
            "Lightweight EVA midsole",
            "Rounded toe box for relaxed fit",
            "Reflective heel tab",
        ],
        "palette": {"upper": "#E8C9A8", "accent": "#111111", "sole": "#FFFFFF", "bg": "#EAEAE7", "style": "lifestyle"},
        "featured": 0,
    },
    {
        "slug": "summit-ridge",
        "name": "AEROSTRIDE SUMMIT RIDGE",
        "category": "Trail",
        "price": 11999,
        "sizes": [6, 7, 8, 9, 10, 11],
        "tagline": "Long days above the treeline.",
        "description": (
            "Our most protective trail shoe. A water-resistant upper, deep "
            "lugs and a cushioned, stable platform keep you moving through "
            "all-day mountain adventures."
        ),
        "features": [
            "Water-resistant weather-shield upper",
            "7 mm deep-grip lugs",
            "Reinforced toe cap and heel lock",
            "Dual-density stable midsole",
        ],
        "palette": {"upper": "#8A5A2B", "accent": "#EAEAE7", "sole": "#111111", "bg": "#EAEAE7", "style": "trail"},
        "featured": 0,
    },
]

# Gallery views produced by tools/make_art.py for every product.
GALLERY_VIEWS = ["side", "angle", "detail"]

REVIEWS = [
    {
        "name": "Aarav M.",
        "city": "Pune",
        "product": "Velocity X",
        "text": "Illustrative review: the carbon plate feels springy without being harsh. Great for tempo runs.",
        "rating": 5,
    },
    {
        "name": "Meera K.",
        "city": "Bengaluru",
        "product": "Apex Runner",
        "text": "Illustrative review: comfortable from the first run, with plenty of cushioning for long weekend miles.",
        "rating": 5,
    },
    {
        "name": "Rohan S.",
        "city": "Mumbai",
        "product": "Nexus Pro",
        "text": "Illustrative review: stable for lifts and light enough for conditioning. Fit true to size.",
        "rating": 4,
    },
]
