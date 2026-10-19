import os
import base64
from pathlib import Path
import pytest
from dotenv import load_dotenv

creds_candidates = [
    os.environ.get('TMTRACK_CREDS_FILE'),
    str(Path.home() / '.tmtrack.creds'),
    str(Path.cwd() / '.tmtrack.creds'),
    str(Path.cwd() / 'live-tests' / '.tmtrack.creds'),
]

for candidate in creds_candidates:
    if candidate and os.path.exists(candidate):
        load_dotenv(candidate)
        break

@pytest.fixture(scope='session')
def creds():
    base_url = os.getenv('TMTRACK_BASE_URL', 'https://diederich.ai').rstrip('/')
    api_url = os.getenv('TMTRACK_API_URL', f'{base_url}/tmtrack/api/v1').rstrip('/')
    auth_api_url = os.getenv('TMTRACK_AUTH_API_URL', f'{base_url}/tmtrack/api/auth').rstrip('/')
    ui_url = os.getenv('TMTRACK_UI_URL', f'{base_url}/tmtrack/')
    auth_token = os.getenv('TMTRACK_AUTH_TOKEN')
    userid = os.getenv('TMTRACK_USERID', 'service-agent')
    password = os.getenv('TMTRACK_PASSWORD')
    alt_token = os.getenv('TMTRACK_ALT_TOKEN')
    alt_userid = os.getenv('TMTRACK_ALT_USERID', 'service-automation')
    admin_token = os.getenv('TMTRACK_ADMIN_TOKEN')
    admin_userid = os.getenv('TMTRACK_ADMIN_USERID', 'dana')
    headless_chrome_cdp = os.getenv('HEADLESS_CHROME_CDP', 'http://127.0.0.1:9333')
    alerta_endpoint = os.getenv('ALERTA_ENDPOINT', 'http://192.168.1.247:8080/api')

    if not auth_token:
        pytest.fail('TMTRACK_AUTH_TOKEN is required. Ensure ~/.tmtrack.creds exists or set TMTRACK_AUTH_TOKEN.')
    if not alt_token:
        pytest.fail('TMTRACK_ALT_TOKEN is required. Ensure ~/.tmtrack.creds exists or set TMTRACK_ALT_TOKEN.')

    return {
        'base_url': base_url,
        'api_url': api_url,
        'auth_api_url': auth_api_url,
        'ui_url': ui_url,
        'auth_token': auth_token,
        'userid': userid,
        'password': password,
        'alt_token': alt_token,
        'alt_userid': alt_userid,
        'admin_token': admin_token,
        'admin_userid': admin_userid,
        'headless_chrome_cdp': headless_chrome_cdp,
        'alerta_endpoint': alerta_endpoint,
    }

@pytest.fixture
def auth_headers(creds):
    return {'Authorization': f'Bearer {creds["auth_token"]}'}

@pytest.fixture
def alt_headers(creds):
    return {'Authorization': f'Bearer {creds["alt_token"]}'}

@pytest.fixture
def basic_auth_headers(creds):
    if not creds.get('password'):
        pytest.skip('TMTRACK_PASSWORD not set in ~/.tmtrack.creds')
    pair = f'{creds["userid"]}:{creds["password"]}'
    encoded = base64.b64encode(pair.encode()).decode()
    return {'Authorization': f'Basic {encoded}'}
