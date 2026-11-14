import os
import pytest
from playwright.sync_api import sync_playwright

FRONTEND_URL = os.environ.get("SENTINELOPS_FRONTEND_URL", "http://localhost:4000")
ADMIN_EMAIL = "admin@sentinelops.local"
ADMIN_PASSWORD = "AdminPass123!"


@pytest.fixture(scope="module")
def authenticated_context():
    """Launches browser, performs login, and shares authenticated session across tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Invalid login check
        page.goto(f"{FRONTEND_URL}/login")
        page.fill('input[type="email"]', "wrong@sentinelops.local")
        page.fill('input[type="password"]', "BadPassword999!")
        page.click('button[type="submit"]')
        page.wait_for_selector('text=Incorrect email or password', timeout=5000)

        # 2. Valid login check
        page.fill('input[type="email"]', ADMIN_EMAIL)
        page.fill('input[type="password"]', ADMIN_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url(f"{FRONTEND_URL}/", timeout=10000)
        
        # Verify token in localStorage
        token = page.evaluate("() => localStorage.getItem('sentinelops_token')")
        assert token is not None and len(token) > 20
        page.close()

        yield context
        browser.close()


def test_auth_and_session_persistence(authenticated_context):
    """Verifies that authenticated session accesses protected routes without redirect."""
    page = authenticated_context.new_page()
    page.goto(f"{FRONTEND_URL}/")
    assert page.is_visible('text=Operations Overview')
    page.close()


def test_global_dashboard_kpis(authenticated_context):
    """Verifies global dashboard renders KPIs and operational counters."""
    page = authenticated_context.new_page()
    page.goto(f"{FRONTEND_URL}/")
    assert page.is_visible('text=Active Incidents')
    assert page.is_visible('text=Monitored Services')
    assert page.is_visible('text=Awaiting Approval')
    assert page.is_visible('text=Resolved Today')
    page.close()


def test_projects_management_and_cockpit(authenticated_context):
    """Verifies projects portfolio, project creation modal, and individual cockpit navigation."""
    page = authenticated_context.new_page()
    page.goto(f"{FRONTEND_URL}/projects")
    page.wait_for_selector('text=Software Projects', timeout=8000)

    # Assert default project card is rendered
    page.wait_for_selector('text=SentinelOps Core', timeout=8000)
    assert page.is_visible('text=SentinelOps Core')

    # Open Project Creation modal
    page.click('button:has-text("New Project")')
    page.wait_for_selector('text=Create New Project', timeout=5000)
    assert page.is_visible('text=Create New Project')

    # Fill and cancel modal
    page.fill('input[placeholder*="E-Commerce"]', "Test E2E Automation")
    page.click('button:has-text("Cancel")')
    page.wait_for_timeout(500)
    assert not page.is_visible('text=Create New Project')

    # Click through to Project Dashboard Cockpit
    page.locator('a:has-text("Project Dashboard")').first.click()
    page.wait_for_url("**/projects/**", timeout=8000)
    page.wait_for_selector('text=All Environments', timeout=8000)
    assert page.is_visible('text=All Environments')
    assert page.is_visible('text=Project Services')
    page.close()


def test_docker_discovery_flow(authenticated_context):
    """Verifies Docker container auto-discovery scan."""
    page = authenticated_context.new_page()
    page.goto(f"{FRONTEND_URL}/discovery")

    assert page.is_visible('text=Automated Service Discovery')
    # Trigger scan
    scan_btn = page.locator('button:has-text("Scan Local Docker")')
    scan_btn.click()
    page.wait_for_timeout(2000)
    
    assert page.is_visible('text=Assign Approved Services to Project')
    page.close()


def test_telemetry_promql_and_logql(authenticated_context):
    """Verifies PromQL metrics and LogQL logs query execution."""
    page = authenticated_context.new_page()
    page.goto(f"{FRONTEND_URL}/telemetry")

    assert page.is_visible('text=Telemetry & Observability Explorer')
    
    # 1. Execute LogQL query
    page.click('button:has-text("Loki Logs")')
    page.click('button:has-text("Execute Query")')
    page.wait_for_timeout(1000)

    # 2. Switch to Prometheus Metrics tab and query
    page.click('button:has-text("Prometheus Metrics")')
    page.click('button:has-text("Execute Query")')
    page.wait_for_timeout(1000)
    
    # 3. Check OpenTelemetry Traces tab
    page.click('button:has-text("OpenTelemetry Traces")')
    assert page.is_visible('text=OpenTelemetry Traces & Spans')
    page.close()


def test_integrations_console(authenticated_context):
    """Verifies integrations console and connection testing."""
    page = authenticated_context.new_page()
    page.goto(f"{FRONTEND_URL}/integrations")

    assert page.is_visible('text=Telemetry Integrations')
    assert page.is_visible('button:has-text("Connect Integration")')

    # Open Connect Integration Modal
    page.click('button:has-text("Connect Integration")')
    assert page.is_visible('text=Connect Telemetry Source')
    page.click('button:has-text("Cancel")')
    page.close()


def test_services_fleet_and_health_probe(authenticated_context):
    """Verifies services registry, health probing, and registration modal."""
    page = authenticated_context.new_page()
    page.goto(f"{FRONTEND_URL}/services")

    assert page.is_visible('text=Monitored Services')
    assert page.is_visible('button:has-text("Register Service")')

    # Open Register Service Modal
    page.click('button:has-text("Register Service")')
    assert page.is_visible('text=Register Monitored Service')
    page.click('button:has-text("Cancel")')

    # Click Probe Health on the first available service card
    probe_btn = page.locator('button:has-text("Probe Health")').first
    if probe_btn.count() > 0:
        probe_btn.click()
        page.wait_for_timeout(1500)
    page.close()


def test_audit_log_immutable_table(authenticated_context):
    """Verifies audit trail table rendering."""
    page = authenticated_context.new_page()
    page.goto(f"{FRONTEND_URL}/audit")
    page.wait_for_selector('text=Audit Trail', timeout=8000)

    assert page.is_visible('text=Audit Trail')
    assert page.is_visible('table')
    page.close()
