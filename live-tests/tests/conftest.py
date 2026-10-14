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
    return {
        "base_url": os.getenv("TMTRACK_BASE_URL", "https://www.realms.org").rstrip("/"),
        "api_url": os.getenv("TMTRACK_API_URL", "https://www.realms.org/api/v1").rstrip("/"),
        "ui_url": os.getenv("TMTRACK_UI_URL", "https://www.realms.org/tmtrack/"),
        "auth_token": os.getenv("TMTRACK_AUTH_TOKEN", "c379025dd04a981bd81d"),
        "userid": os.getenv("TMTRACK_USERID", "TemporaryHero"),
        "alt_token": os.getenv("TMTRACK_ALT_TOKEN", "d4b69c69dd0059b59bcc"),
        "alt_userid": os.getenv("TMTRACK_ALT_USERID", "WanderingPixel"),
        "headless_chrome_cdp": os.getenv("HEADLESS_CHROME_CDP", "http://127.0.0.1:9333"),
    }

@pytest.fixture
def auth_headers(creds):
    return {"Authorization": f"Bearer {creds['auth_token']}"}

@pytest.fixture
def alt_headers(creds):
    return {"Authorization": f"Bearer {creds['alt_token']}"}
