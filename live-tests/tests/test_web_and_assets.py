import httpx
import pytest

def test_tmtrack_ui_html_served_properly(creds):
    url = creds["ui_url"]
    resp = httpx.get(url, timeout=10.0, follow_redirects=True)
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    content = resp.text

    # Title & Core DOM elements
    assert "Time Tracker UI" in content
    assert "user-select-dropdown" in content
    assert "task-list-container" in content
    assert "categories-modal" in content
    assert "edit-categories-btn" in content
    assert "new-day-btn" in content

    # Newly added production elements (ensures deployment fidelity)
    assert "refresh-btn" in content
    assert "totals-display" in content
    assert "total-expected-hours" in content
    assert "total-actual-hours" in content

    # External dependencies & scripts
    assert "pikaday.css" in content
    assert "moment.min.js" in content
    assert "pikaday.js" in content
    assert "js/app.js" in content
    assert "css/styles.css" in content


def test_tmtrack_static_css_assets(creds):
    css_url = f"{creds['ui_url']}css/styles.css"
    resp = httpx.get(css_url, timeout=10.0)
    assert resp.status_code == 200
    assert "text/css" in resp.headers.get("content-type", "")
    css_text = resp.text
    assert len(css_text) > 1000

    # Content-level fidelity assertions
    assert "#refresh-btn" in css_text
    assert "#totals-display" in css_text
    assert ".task-field-description textarea" in css_text
    assert ".stepper-arrows" in css_text
    assert ".number-input-wrapper" in css_text


def test_tmtrack_static_js_assets(creds):
    js_url = f"{creds['ui_url']}js/app.js"
    resp = httpx.get(js_url, timeout=10.0)
    assert resp.status_code == 200
    assert "javascript" in resp.headers.get("content-type", "")
    js_text = resp.text
    assert len(js_text) > 5000

    # Content-level fidelity assertions for critical app logic
    assert "decimalToFraction" in js_text
    assert "fractionToDecimal" in js_text
    assert "getApiPrefix" in js_text
    assert "updateTotals" in js_text
    assert "backgroundRefresh" in js_text
    assert "Pikaday" in js_text


def test_tmtrack_favicon(creds):
    fav_url = f"{creds['ui_url']}favicon.ico"
    resp = httpx.get(fav_url, timeout=10.0)
    assert resp.status_code == 200
    assert len(resp.content) > 500


def test_nginx_api_proxy_routing_locations(creds, auth_headers):
    """
    Asserts that both /api/v1 and legacy /api locations are properly routed by Nginx
    to the backend uwsgi application container, and invalid endpoints return 404.
    """
    base_url = creds["base_url"]
    
    # Test /api/v1 prefix
    v1_resp = httpx.get(f"{base_url}/api/v1/categories", headers=auth_headers, timeout=10.0)
    assert v1_resp.status_code == 200
    assert "categories" in v1_resp.json()

    # Test /api prefix without v1 reaches Flask (proxied by Nginx, returns 404 from Flask because blueprints are /api/v1)
    legacy_resp = httpx.get(f"{base_url}/api/categories", headers=auth_headers, timeout=10.0)
    assert legacy_resp.status_code == 404
    # Ensure it was handled by Flask backend rather than Nginx 502
    assert legacy_resp.status_code != 502

    # Test unrouted API path returns 404
    probe_resp = httpx.get(f"{base_url}/api/v1/unrouted_probe_xyz", headers=auth_headers, timeout=10.0)
    assert probe_resp.status_code == 404
