import httpx
import pytest

def test_tmtrack_ui_html_served_properly(creds):
    url = creds["ui_url"]
    resp = httpx.get(url, timeout=10.0, follow_redirects=True)
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    content = resp.text
    assert "Time Tracker UI" in content
    assert "user-select-dropdown" in content
    assert "task-list-container" in content
    assert "categories-modal" in content
    assert "edit-categories-btn" in content

def test_tmtrack_static_css_assets(creds):
    css_url = f"{creds['ui_url']}css/styles.css"
    resp = httpx.get(css_url, timeout=10.0)
    assert resp.status_code == 200
    assert "text/css" in resp.headers.get("content-type", "")
    assert len(resp.content) > 1000

def test_tmtrack_static_js_assets(creds):
    js_url = f"{creds['ui_url']}js/app.js"
    resp = httpx.get(js_url, timeout=10.0)
    assert resp.status_code == 200
    assert "javascript" in resp.headers.get("content-type", "")
    assert len(resp.content) > 5000

def test_tmtrack_favicon(creds):
    fav_url = f"{creds['ui_url']}favicon.ico"
    resp = httpx.get(fav_url, timeout=10.0)
    assert resp.status_code == 200

def test_api_v1_categories_proxy(creds, auth_headers):
    resp_v1 = httpx.get(f"{creds['api_url']}/categories", headers=auth_headers, timeout=10.0)
    assert resp_v1.status_code == 200
    assert "categories" in resp_v1.json()

def test_api_v1_tasks_proxy(creds, auth_headers):
    resp = httpx.get(f"{creds['api_url']}/tasks", headers=auth_headers, timeout=10.0)
    assert resp.status_code == 200
    assert resp.json().get("status") == "success"
