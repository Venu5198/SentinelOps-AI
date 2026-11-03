import asyncio
import os
from playwright.async_api import async_playwright

SCREENSHOT_DIR = "docs/screenshots/readme"

async def capture_all_screenshots():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # 1. Login Page
        print("[*] 1. Capturing login.png...")
        await page.goto("http://localhost:3000/login", wait_until="networkidle")
        await page.wait_for_selector("text=SentinelOps AI")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/login.png")

        # Authenticate
        print("[*] Authenticating...")
        await page.fill("input[type='email']", "admin@sentinelops.com")
        await page.fill("input[type='password']", "AdminPass123!")
        await page.click("button[type='submit']")
        await page.wait_for_url("http://localhost:3000/", timeout=8000)
        await page.wait_for_selector("text=Operations Overview")
        await page.wait_for_timeout(1000)

        # 2. Main Dashboard
        print("[*] 2. Capturing dashboard.png...")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/dashboard.png")

        # 3. Incident List
        print("[*] 3. Capturing incidents.png...")
        await page.goto("http://localhost:3000/incidents", wait_until="networkidle")
        await page.wait_for_selector("h1:has-text('Incidents')")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/incidents.png")

        # 4. Incident Detail Top View (INC-4CE61E)
        print("[*] 4. Capturing incident-detail.png for INC-4CE61E...")
        await page.goto("http://localhost:3000/incidents/INC-4CE61E", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.screenshot(path=f"{SCREENSHOT_DIR}/incident-detail.png")

        # 5. AI Investigation Result (Top of AI Card)
        print("[*] 5. Capturing ai-investigation.png...")
        await page.evaluate("window.scrollTo(0, 100)")
        await page.wait_for_timeout(500)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/ai-investigation.png")

        # 6. Remediation Approval Gate (Scrolled into view)
        print("[*] 6. Capturing remediation-approval.png...")
        approval_gate = page.locator("text=Human Approval Gate")
        if await approval_gate.count() > 0:
            await approval_gate.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/remediation-approval.png")
        else:
            await page.evaluate("window.scrollTo(0, 320)")
            await page.wait_for_timeout(500)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/remediation-approval.png")

        # 7. Evidence Analysis (Scrolled into view)
        print("[*] 7. Capturing evidence-analysis.png...")
        evi_section = page.locator("h2:has-text('Diagnostic Evidence')")
        if await evi_section.count() > 0:
            await evi_section.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/evidence-analysis.png")
        else:
            await page.evaluate("window.scrollTo(0, 550)")
            await page.wait_for_timeout(500)
            await page.screenshot(path=f"{SCREENSHOT_DIR}/evidence-analysis.png")

        # 8. Services Monitoring
        print("[*] 8. Capturing services.png...")
        await page.goto("http://localhost:3000/services", wait_until="networkidle")
        await page.wait_for_selector("h1:has-text('Monitored Services')")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/services.png")

        # 9. Audit Logs
        print("[*] 9. Capturing audit-logs.png...")
        await page.goto("http://localhost:3000/audit", wait_until="networkidle")
        await page.wait_for_selector("h1:has-text('Audit Trail')")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/audit-logs.png")

        await browser.close()
        print("[+] All 9 screenshots captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture_all_screenshots())
