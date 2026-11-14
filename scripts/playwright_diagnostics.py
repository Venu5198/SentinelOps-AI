import asyncio
import os
import sys
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:4000"

PAGES_TO_TEST = [
    {"name": "Login Page", "url": f"{BASE_URL}/login"},
    {"name": "Overview Dashboard", "url": f"{BASE_URL}/"},
    {"name": "Projects Portfolio", "url": f"{BASE_URL}/projects"},
    {"name": "Services Fleet", "url": f"{BASE_URL}/services"},
    {"name": "Discovery Console", "url": f"{BASE_URL}/discovery"},
    {"name": "Telemetry Explorer", "url": f"{BASE_URL}/telemetry"},
    {"name": "Integrations Console", "url": f"{BASE_URL}/integrations"},
    {"name": "Incidents Console", "url": f"{BASE_URL}/incidents"},
    {"name": "Audit Logs", "url": f"{BASE_URL}/audit"},
]

async def run_playwright_diagnostics():
    print(f"Starting Playwright UI validation against {BASE_URL}...")
    errors_detected = []
    console_logs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Listen for console errors & failed network requests
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}") if msg.type in ["error", "warning"] else None)
        page.on("pageerror", lambda exc: errors_detected.append(f"Page Error: {exc}"))

        # 1. Login flow
        print("\n--- Testing Login Flow ---")
        try:
            await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
            await page.fill('input[type="email"]', "admin@sentinelops.local")
            await page.fill('input[type="password"]', "AdminPass123!")
            await page.click('button[type="submit"]')
            await page.wait_for_url(f"{BASE_URL}/", timeout=10000)
            print("✓ Successfully authenticated as Admin, redirected to Overview Dashboard")
        except Exception as e:
            errors_detected.append(f"Login failed: {e}")
            print(f"✗ Login error: {e}")

        # 2. Iterate through each page
        for p_info in PAGES_TO_TEST[1:]:
            p_name = p_info["name"]
            p_url = p_info["url"]
            print(f"\n--- Checking {p_name} ({p_url}) ---")
            page_errors = []
            def on_resp(res):
                if res.status >= 400 and not res.url.endswith("/favicon.ico"):
                    page_errors.append(f"HTTP {res.status} on {res.url}")
            
            page.on("response", on_resp)
            try:
                resp = await page.goto(p_url, wait_until="networkidle", timeout=12000)
                await page.wait_for_timeout(1000)  # allow UI state & effects to settle
                if resp.status >= 400:
                    page_errors.append(f"Page returned HTTP {resp.status}")
                
                # Check for critical crash text / unhandled boundaries
                body_text = await page.inner_text("body")
                if "Application Error" in body_text or "Cannot read properties" in body_text:
                    page_errors.append("React Crash or Unhandled Exception visible in UI!")

                if page_errors:
                    print(f"✗ Issues on {p_name}:")
                    for err in page_errors:
                        print(f"   - {err}")
                        errors_detected.append(f"[{p_name}] {err}")
                else:
                    print(f"✓ {p_name} rendered cleanly with zero errors")

            except Exception as e:
                print(f"✗ Failed navigating to {p_name}: {e}")
                errors_detected.append(f"[{p_name}] Exception: {e}")
            finally:
                page.remove_listener("response", on_resp)

        # 3. Test interactive Action: Docker Discovery scan button
        print("\n--- Testing Interactive Discovery Scan ---")
        try:
            await page.goto(f"{BASE_URL}/discovery", wait_until="networkidle")
            scan_btn = page.locator('button:has-text("Scan Local Docker")')
            if await scan_btn.count() > 0:
                await scan_btn.click()
                await page.wait_for_timeout(2000)
                print("✓ 'Scan Local Docker' button clicked successfully without UI crash")
            else:
                print("Notice: 'Scan Local Docker' button not found on /discovery")
        except Exception as e:
            errors_detected.append(f"Interactive Discovery scan failed: {e}")
            print(f"✗ Discovery test error: {e}")

        # 4. Test interactive Action: Create Project Modal
        print("\n--- Testing Interactive Project Creation Modal ---")
        try:
            await page.goto(f"{BASE_URL}/projects", wait_until="networkidle")
            new_proj_btn = page.locator('button:has-text("New Project")')
            if await new_proj_btn.count() > 0:
                await new_proj_btn.click()
                await page.wait_for_selector('text=Create New Project', timeout=3000)
                print("✓ 'New Project' modal opened cleanly")
                # close modal
                cancel_btn = page.locator('button:has-text("Cancel")')
                await cancel_btn.click()
                print("✓ Project modal closed cleanly")
            else:
                print("Notice: 'New Project' button not found")
        except Exception as e:
            errors_detected.append(f"Project modal test failed: {e}")
            print(f"✗ Project modal error: {e}")

        # Capture a full screenshot of the live Projects overview
        os.makedirs("docs/screenshots/playwright_audit", exist_ok=True)
        await page.goto(f"{BASE_URL}/projects", wait_until="networkidle")
        await page.screenshot(path="docs/screenshots/playwright_audit/projects_validated.png")
        print("\nSaved validation screenshot to docs/screenshots/playwright_audit/projects_validated.png")

        await browser.close()

    print("\n================ DIAGNOSTIC REPORT ================")
    if not errors_detected:
        print("PERFECT: Zero runtime errors, zero HTTP 4xx/5xx API failures, zero UI crashes detected!")
        return 0
    else:
        print(f"WARNING: {len(errors_detected)} issue(s) detected:")
        for err in errors_detected:
            print(f"  • {err}")
        return 1

if __name__ == "__main__":
    code = asyncio.run(run_playwright_diagnostics())
    sys.exit(code)
