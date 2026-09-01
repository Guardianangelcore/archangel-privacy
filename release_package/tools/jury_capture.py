#!/usr/bin/env python3
"""Capture the 4 jury screenshots locally into /app/jury_assets/."""
import asyncio, os
from playwright.async_api import async_playwright

URL = "http://localhost:3000"
OUT = "/app/jury_assets"
os.makedirs(OUT, exist_ok=True)

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                                           args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = await browser.new_page(viewport={"width": 390, "height": 844})
        await page.goto(URL, wait_until="domcontentloaded")
        try:
            await page.wait_for_selector("#root div", timeout=120000)
        except Exception:
            html = await page.content()
            print("DEBUG title:", await page.title(), "| html len:", len(html))
            await page.screenshot(path=f"{OUT}/debug.png")
            raise
        await page.wait_for_timeout(4000)
        try:
            await page.get_by_test_id("founder-bypass-btn").click(timeout=8000)
            await page.wait_for_timeout(4000)
            print("logged in")
        except Exception:
            print("already logged in")
        await page.wait_for_selector('[data-testid="standard-home"]', timeout=30000)
        await page.wait_for_timeout(2500)
        await page.screenshot(path=f"{OUT}/home.png")
        print("home ok")
        await page.goto(f"{URL}/jarvis", wait_until="domcontentloaded")
        await page.wait_for_selector('[data-testid="jarvis-screen"]', timeout=30000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=f"{OUT}/jarvis.png")
        print("jarvis ok")
        await page.goto(f"{URL}/magic-lens", wait_until="domcontentloaded")
        await page.wait_for_selector('[data-testid="ml-open-camera"]', timeout=30000)
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/lens.png")
        print("lens ok")
        await page.goto(f"{URL}/fall-verify", wait_until="domcontentloaded")
        await page.wait_for_selector('[data-testid="fall-verify-screen"]', timeout=30000)
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/fall.png")
        print("fall ok")
        await browser.close()

asyncio.run(main())
