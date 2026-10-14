import pytest
from playwright.sync_api import sync_playwright

@pytest.fixture
def browser_page(creds):
    cdp_url = creds.get("headless_chrome_cdp", "http://127.0.0.1:9333")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            pytest.skip(f"Headless browser CDP endpoint not reachable at {cdp_url}: {e}")

        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        try:
            yield page
        finally:
            context.close()
            browser.close()

def test_browser_ui_load_and_auth_token_ingestion(browser_page, creds):
    auth_url = f"{creds['ui_url']}?auth_token={creds['auth_token']}"
    response = browser_page.goto(auth_url, wait_until="networkidle", timeout=30000)
    assert response is not None
    assert response.status == 200

    # Verify page title
    title = browser_page.title()
    assert "Time Tracker UI" in title

    # Verify query param was stripped and saved to cookie
    current_url = browser_page.url
    assert "auth_token=" not in current_url

    cookies = browser_page.context.cookies()
    token_cookie = next((c for c in cookies if c["name"] == "auth_token"), None)
    assert token_cookie is not None
    assert token_cookie["value"] == creds["auth_token"]

    # Verify user dropdown loaded
    user_select = browser_page.locator("#user-select-dropdown")
    user_select.wait_for(state="visible", timeout=10000)
    options = user_select.locator("option").all_text_contents()
    assert len(options) > 0
    assert creds["userid"] in options

def test_browser_non_admin_rbac_hides_categories_editor(browser_page, creds):
    auth_url = f"{creds['ui_url']}?auth_token={creds['auth_token']}"
    browser_page.goto(auth_url, wait_until="networkidle", timeout=30000)

    # RBAC assertion: non-admin test users must NOT see the Categories button
    categories_btn = browser_page.locator("#edit-categories-btn")
    assert not categories_btn.is_visible(), "Non-admin test user must not have visible Categories button"

def test_browser_add_task_button_creates_row(browser_page, creds):
    auth_url = f"{creds['ui_url']}?auth_token={creds['auth_token']}"
    browser_page.goto(auth_url, wait_until="networkidle", timeout=30000)

    # Click Add Task button
    add_task_btn = browser_page.locator("#add-task-btn")
    add_task_btn.wait_for(state="visible", timeout=5000)
    add_task_btn.click()

    # Verify task list container receives a new task entry
    task_container = browser_page.locator("#task-list-container")
    task_container.wait_for(state="visible", timeout=5000)
    inputs = task_container.locator("input, select").count()
    assert inputs > 0, "Clicking Add Task should render task input controls in task-list-container"
