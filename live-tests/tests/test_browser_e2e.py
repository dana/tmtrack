import uuid
import pytest
from playwright.sync_api import sync_playwright

@pytest.fixture
def browser_page(creds):
    cdp_url = creds.get('headless_chrome_cdp', 'http://127.0.0.1:9333')
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            pytest.fail(f'Headless browser CDP endpoint not reachable at {cdp_url}: {e}')

        # Standard context with strict SSL certificate verification
        context = browser.new_context()
        page = context.new_page()
        try:
            yield page
        finally:
            context.close()
            browser.close()


def test_browser_ui_load_and_auth_token_ingestion(browser_page, creds):
    auth_url = f"{creds['ui_url']}?auth_token={creds['auth_token']}"
    response = browser_page.goto(auth_url, wait_until='networkidle', timeout=30000)
    assert response is not None
    assert response.status == 200

    # Verify page title
    assert 'Time Tracker UI' in browser_page.title()

    # Verify query param was stripped and saved to cookie
    assert 'auth_token=' not in browser_page.url

    cookies = browser_page.context.cookies()
    token_cookie = next((c for c in cookies if c['name'] == 'auth_token'), None)
    assert token_cookie is not None
    assert token_cookie['value'] == creds['auth_token']

    # Verify authenticated user info is rendered
    user_info = browser_page.locator('#user-info-display')
    user_info.wait_for(state='visible', timeout=10000)
    assert creds['userid'] in user_info.text_content()


def test_browser_cookie_persistence_on_subsequent_visit(browser_page, creds):
    auth_url = f"{creds['ui_url']}?auth_token={creds['auth_token']}"
    browser_page.goto(auth_url, wait_until='networkidle', timeout=30000)

    # Subsequent visit without query param
    browser_page.goto(creds['ui_url'], wait_until='networkidle', timeout=30000)
    assert 'auth_token=' not in browser_page.url

    user_info = browser_page.locator('#user-info-display')
    user_info.wait_for(state='visible', timeout=10000)
    assert creds['userid'] in user_info.text_content()


def test_browser_non_admin_rbac_hides_categories_editor(browser_page, creds):
    auth_url = f"{creds['ui_url']}?auth_token={creds['auth_token']}"
    browser_page.goto(auth_url, wait_until='networkidle', timeout=30000)

    user_info = browser_page.locator('#user-info-display')
    user_info.wait_for(state='visible', timeout=10000)

    # Non-admin service accounts must NOT see the Categories edit button
    categories_btn = browser_page.locator('#edit-categories-btn')
    assert not categories_btn.is_visible(), 'Non-admin service account must not have visible Categories button'


def test_browser_add_task_button_creates_row(browser_page, creds):
    auth_url = f"{creds['ui_url']}?auth_token={creds['auth_token']}"
    browser_page.goto(auth_url, wait_until='networkidle', timeout=30000)

    # Ensure task list container is visible
    task_container = browser_page.locator('#task-list-container')
    task_container.wait_for(state='visible', timeout=10000)
    initial_count = task_container.locator('.task-line').count()

    # Click Add Task button
    add_task_btn = browser_page.locator('#add-task-btn')
    add_task_btn.wait_for(state='visible', timeout=5000)
    add_task_btn.click()

    # Verify task count incremented by exactly 1
    new_count = task_container.locator('.task-line').count()
    assert new_count == initial_count + 1

    # Verify newly created line has dirty and incomplete classes
    new_line = task_container.locator('.task-line').last
    classes = new_line.get_attribute('class') or ''
    assert 'dirty' in classes
    assert 'incomplete' in classes

    # Discard unsaved row via delete button
    new_line.locator('.delete-task-btn').click()
    assert task_container.locator('.task-line').count() == initial_count


def test_browser_fraction_stepper_interaction(browser_page, creds):
    auth_url = f"{creds['ui_url']}?auth_token={creds['auth_token']}"
    browser_page.goto(auth_url, wait_until='networkidle', timeout=30000)

    # Add task line
    browser_page.locator('#add-task-btn').click()
    new_line = browser_page.locator('#task-list-container .task-line').last
    expected_input = new_line.locator('.task-input-expected_hours')
    up_arrow = new_line.locator('.task-field-expected_hours .arrow-up')
    down_arrow = new_line.locator('.task-field-expected_hours .arrow-down')

    # Verify stepping increments by 0.25 fractions
    up_arrow.click()
    assert expected_input.input_value() == '1/4'
    up_arrow.click()
    assert expected_input.input_value() == '1/2'
    up_arrow.click()
    assert expected_input.input_value() == '3/4'
    down_arrow.click()
    assert expected_input.input_value() == '1/2'

    # Discard unsaved task line
    new_line.locator('.delete-task-btn').click()


def test_browser_pikaday_calendar_picker(browser_page, creds):
    auth_url = f"{creds['ui_url']}?auth_token={creds['auth_token']}"
    browser_page.goto(auth_url, wait_until='networkidle', timeout=30000)

    # Click New Day button
    browser_page.locator('#new-day-btn').click()

    # Verify Pikaday calendar container becomes visible
    pika = browser_page.locator('.pika-single')
    pika.wait_for(state='visible', timeout=5000)
    assert pika.is_visible()


def test_browser_refresh_button_interaction(browser_page, creds):
    auth_url = f"{creds['ui_url']}?auth_token={creds['auth_token']}"
    browser_page.goto(auth_url, wait_until='networkidle', timeout=30000)

    # Click Refresh button
    refresh_btn = browser_page.locator('#refresh-btn')
    refresh_btn.wait_for(state='visible', timeout=5000)
    refresh_btn.click()

    # Assert container remains visible and functional
    browser_page.locator('#task-list-container').wait_for(state='visible', timeout=5000)
    browser_page.locator('#day-list').wait_for(state='visible', timeout=5000)


def test_browser_task_save_and_delete_lifecycle(browser_page, creds):
    auth_url = f"{creds['ui_url']}?auth_token={creds['auth_token']}"
    browser_page.goto(auth_url, wait_until='networkidle', timeout=30000)

    # Add task line
    browser_page.locator('#add-task-btn').click()
    new_line = browser_page.locator('#task-list-container .task-line').last

    unique_id = uuid.uuid4().hex[:6]
    task_name = f'uitest-{unique_id}'
    new_line.locator('.task-input-task_name').fill(task_name)
    new_line.locator('.task-input-category').select_option(value='work')
    new_line.locator('.task-field-expected_hours .arrow-up').click() # sets 1/4
    new_line.locator('.task-input-description').fill('E2E Playwright test')

    # Click save
    new_line.locator('.save-task-btn').click()

    # Wait for success toast notification
    toast = browser_page.locator('#toast-notification')
    toast.wait_for(state='visible', timeout=5000)
    assert 'Task saved successfully' in toast.text_content()

    task_id = new_line.get_attribute('data-task-id')
    assert task_id is not None
    assert 'dirty' not in (new_line.get_attribute('class') or '')

    # Delete the task via UI with confirm dialog handling
    browser_page.on('dialog', lambda d: d.accept())
    new_line.locator('.delete-task-btn').click()
    browser_page.wait_for_selector(f"#task-list-container .task-line[data-task-id='{task_id}']", state='detached', timeout=5000)


def test_browser_service_account_login_modal(browser_page, creds):
    if not creds.get('password'):
        pytest.skip('TMTRACK_PASSWORD not configured')

    # Start from an unauthenticated context
    browser_page.context.clear_cookies()
    browser_page.goto(creds['ui_url'], wait_until='networkidle', timeout=30000)

    # Click Service Login toggle in guest banner
    service_login_toggle = browser_page.locator('#service-login-toggle')
    service_login_toggle.wait_for(state='visible', timeout=5000)
    service_login_toggle.click()

    # Verify modal opens
    modal = browser_page.locator('#service-login-modal')
    modal.wait_for(state='visible', timeout=5000)

    # Fill credentials
    browser_page.locator('#service-login-username').fill(creds['userid'])
    browser_page.locator('#service-login-password').fill(creds['password'])

    # Submit
    browser_page.locator('#submit-service-login-btn').click()

    # Wait for modal to dismiss and reload to complete
    modal.wait_for(state='hidden', timeout=10000)
    browser_page.wait_for_function(
        f'() => document.querySelector("#user-info-display") && document.querySelector("#user-info-display").textContent.includes("{creds["userid"]}")',
        timeout=15000
    )

    user_info = browser_page.locator('#user-info-display')
    assert creds['userid'] in user_info.text_content()
    assert browser_page.locator('.scope-container').is_visible()
