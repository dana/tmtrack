import os
from pathlib import Path
import pytest
from dotenv import load_dotenv

# Search for credentials file in order:
# 1. TMTRACK_CREDS_FILE env var
# 2. ~/.tmtrack.creds
# 3. .tmtrack.creds in current or parent directory
creds_candidates = [
    os.environ.get("TMTRACK_CREDS_FILE"),
    str(Path.home() / ".tmtrack.creds"),
    str(Path.cwd() / ".tmtrack.creds"),
    str(Path.cwd() / "live-tests" / ".tmtrack.creds"),
]

for candidate in creds_candidates:
    if candidate and os.path.exists(candidate):
        load_dotenv(candidate)
        break

@pytest.fixture(scope="session")
def creds():
    base_url = os.getenv("TMTRACK_BASE_URL", "https://www.realms.org").rstrip("/")
    api_url = os.getenv("TMTRACK_API_URL", f"{base_url}/api/v1").rstrip("/")
    ui_url = os.getenv("TMTRACK_UI_URL", f"{base_url}/tmtrack/")
    auth_token = os.getenv("TMTRACK_AUTH_TOKEN")
    userid = os.getenv("TMTRACK_USERID", "TemporaryHero")
    alt_token = os.getenv("TMTRACK_ALT_TOKEN")
    alt_userid = os.getenv("TMTRACK_ALT_USERID", "WanderingPixel")
    admin_token = os.getenv("TMTRACK_ADMIN_TOKEN")
    admin_userid = os.getenv("TMTRACK_ADMIN_USERID", "dana")
    headless_chrome_cdp = os.getenv("HEADLESS_CHROME_CDP", "http://127.0.0.1:9333")

    if not auth_token:
        pytest.fail("TMTRACK_AUTH_TOKEN is required. Ensure ~/.tmtrack.creds exists or set TMTRACK_AUTH_TOKEN.")
    if not alt_token:
        pytest.fail("TMTRACK_ALT_TOKEN is required. Ensure ~/.tmtrack.creds exists or set TMTRACK_ALT_TOKEN.")

    return {
        "base_url": base_url,
        "api_url": api_url,
        "ui_url": ui_url,
        "auth_token": auth_token,
        "userid": userid,
        "alt_token": alt_token,
        "alt_userid": alt_userid,
        "admin_token": admin_token,
        "admin_userid": admin_userid,
        "headless_chrome_cdp": headless_chrome_cdp,
    }

@pytest.fixture
def auth_headers(creds):
    return {"Authorization": f"Bearer {creds['auth_token']}"}

@pytest.fixture
def alt_headers(creds):
    return {"Authorization": f"Bearer {creds['alt_token']}"}
