"""Rasterise static/images/og-source.svg to og.png (Open Graph needs a raster image).

Requires Playwright with Chromium:  pip install playwright && playwright install chromium
The generated og.png is committed, so this is only needed when the artwork changes.
"""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

IMAGES = Path(__file__).resolve().parent.parent / "static" / "images"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1200, "height": 630})
        await page.goto((IMAGES / "og-source.svg").as_uri())
        await page.screenshot(path=str(IMAGES / "og.png"))
        await browser.close()


asyncio.run(main())
