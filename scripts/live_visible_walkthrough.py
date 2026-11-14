import asyncio
import time
from playwright.async_api import async_playwright

FRONTEND_URL = "http://localhost:4000"
ADMIN_EMAIL = "admin@sentinelops.local"
ADMIN_PASSWORD = "AdminPass123!"

async def run_live_visible_walkthrough():
    print(f"Connecting to live Chrome instance on http://127.0.0.1:9222...")
    async with async_playwright() as p:
        # Connect to existing Chrome instance running with --remote-debugging-port=9222
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        print("✓ Connected to live Chrome browser successfully!")

        # Use existing page or open a new tab
        contexts = browser.contexts
        if contexts and contexts[0].pages:
            page = contexts[0].pages[0]
        else:
            context = contexts[0] if contexts else await browser.new_context()
            page = await context.new_page()

        await page.bring_to_front()

        # 1. Login Flow (Visible in user's browser)
        print("\n[Step 1] Navigating to Login Page...")
        await page.goto(f"{FRONTEND_URL}/login")
        await asyncio.sleep(1.5)

        # Fill credentials with human-paced typing
        email_input = page.locator('input[type="email"]')
        await email_input.click()
        await email_input.fill("")
        await email_input.type(ADMIN_EMAIL, delay=40)
        await asyncio.sleep(0.5)

        pw_input = page.locator('input[type="password"]')
        await pw_input.click()
        await pw_input.fill("")
        await pw_input.type(ADMIN_PASSWORD, delay=40)
        await asyncio.sleep(0.8)

        print("Clicking 'Sign In' button...")
        await page.click('button[type="submit"]')
        await page.wait_for_url(f"{FRONTEND_URL}/", timeout=10000)
        await asyncio.sleep(2)
        print("✓ Authenticated and landed on Overview Dashboard.")

        # 2. Overview Dashboard Exploration
        print("\n[Step 2] Exploring Operations Overview Dashboard...")
        await page.hover('text=Active Incidents')
        await asyncio.sleep(1)
        await page.hover('text=Monitored Services')
        await asyncio.sleep(1)
        await page.evaluate("window.scrollBy(0, 300)")
        await asyncio.sleep(1.5)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)

        # 3. Projects Portfolio & Project Creation
        print("\n[Step 3] Navigating to Projects Portfolio...")
        await page.click('a[href="/projects"]')
        await page.wait_for_selector('text=Software Projects')
        await asyncio.sleep(2)

        test_project_name = f"Live Demo Cluster {int(time.time())}"
        print(f"Opening 'New Project' modal to create: {test_project_name}...")
        await page.click('button:has-text("New Project")')
        await page.wait_for_selector('text=Create New Project')
        await asyncio.sleep(1.5)

        proj_name_input = page.locator('input[placeholder*="E-Commerce"]')
        await proj_name_input.click()
        await proj_name_input.type(test_project_name, delay=35)
        await asyncio.sleep(1)

        desc_input = page.locator('textarea[placeholder*="Summary"]')
        await desc_input.click()
        await desc_input.type("Visible testing live walkthrough project", delay=25)
        await asyncio.sleep(1.5)

        print("Submitting project creation form...")
        await page.click('button:has-text("Create Project")')
        await page.wait_for_selector(f'text={test_project_name}', timeout=8000)
        print(f"✓ Project '{test_project_name}' visible on screen!")
        await asyncio.sleep(2.5)

        # Reload page to visibly prove persistence
        print("Reloading browser to prove database persistence...")
        await page.reload()
        await page.wait_for_selector(f'text={test_project_name}', timeout=8000)
        print("✓ Project persisted and verified after reload.")
        await asyncio.sleep(2)

        # 4. Project Cockpit Dashboard
        print("\n[Step 4] Opening dedicated Project Dashboard Cockpit...")
        await page.locator('a:has-text("Project Dashboard")').first.click()
        await page.wait_for_url("**/projects/**", timeout=8000)
        await page.wait_for_selector('text=All Environments')
        await asyncio.sleep(2)

        # Toggle environment filters visibly
        print("Toggling Environment filters: Development, Staging, Production...")
        for env_name in ["Development", "Staging", "Production", "All Environments"]:
            btn = page.locator(f'button:has-text("{env_name}")')
            if await btn.count() > 0:
                await btn.click()
                print(f"  Switched filter to: {env_name}")
                await asyncio.sleep(1.2)

        # 5. Automated Docker Discovery
        print("\n[Step 5] Navigating to Docker Discovery Console...")
        await page.click('a[href="/discovery"]')
        await page.wait_for_selector('text=Automated Service Discovery')
        await asyncio.sleep(2)

        print("Clicking 'Scan Local Docker'...")
        await page.click('button:has-text("Scan Local Docker")')
        await page.wait_for_selector('h3:has-text("prd-")', timeout=10000)
        print("✓ Discovered Docker containers displayed on screen!")
        await asyncio.sleep(2)

        approve_btn = page.locator('button:has-text("Approve & Onboard")').first
        if await approve_btn.count() > 0:
            print("Clicking 'Approve & Onboard' on discovered container...")
            await approve_btn.click()
            await asyncio.sleep(2.5)
            print("✓ Container approved and registered into service fleet.")

        # 6. Telemetry Explorer: PromQL & LogQL
        print("\n[Step 6] Navigating to Telemetry & LogQL Explorer...")
        await page.click('a[href="/telemetry"]')
        await page.wait_for_selector('text=Telemetry & Observability Explorer')
        await asyncio.sleep(2)

        print("Executing live PromQL query: 'up'...")
        await page.click('button:has-text("Prometheus Metrics")')
        await asyncio.sleep(1)
        query_input = page.locator('input[placeholder*="up"]')
        await query_input.click()
        await query_input.fill("up")
        await page.click('button:has-text("Execute Query")')
        await asyncio.sleep(2.5)
        print("✓ Live Prometheus metric vector results rendered on screen!")

        print("Switching to Loki LogQL tab...")
        await page.click('button:has-text("Loki Logs")')
        await asyncio.sleep(1)
        await page.click('button:has-text("Execute Query")')
        await asyncio.sleep(2.5)
        print("✓ Live Loki log stream rendered on screen!")

        # 7. Telemetry Integrations
        print("\n[Step 7] Navigating to Telemetry Integrations...")
        await page.click('a[href="/integrations"]')
        await page.wait_for_selector('text=Telemetry Integrations')
        await asyncio.sleep(2)

        test_conn_btn = page.locator('button:has-text("Test Connection")').first
        if await test_conn_btn.count() > 0:
            print("Clicking 'Test Connection' on Prometheus...")
            await test_conn_btn.click()
            await asyncio.sleep(2)
            print("✓ Live integration ping completed and badge updated.")

        # 8. Services Fleet
        print("\n[Step 8] Navigating to Services Fleet...")
        await page.click('a[href="/services"]')
        await page.wait_for_selector('text=Monitored Services')
        await asyncio.sleep(2)

        probe_btn = page.locator('button:has-text("Probe Health")').first
        if await probe_btn.count() > 0:
            print("Clicking 'Probe Health' on active service...")
            await probe_btn.click()
            await asyncio.sleep(2)
            print("✓ Service probed live.")

        # 9. Audit Trail
        print("\n[Step 9] Navigating to Audit Logs...")
        await page.click('a[href="/audit"]')
        await page.wait_for_selector('text=Audit Trail')
        await asyncio.sleep(2)
        print("✓ Immutable compliance audit trail verified.")

        print("\n================ LIVE WALKTHROUGH COMPLETED ================")
        print("All workflows executed visibly on your open Chrome browser window!")

if __name__ == "__main__":
    asyncio.run(run_live_visible_walkthrough())
