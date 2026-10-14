import httpx
import pytest

def test_get_categories_success(creds, auth_headers):
    url = f"{creds['api_url']}/categories"
    resp = httpx.get(url, headers=auth_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) > 0
    # Core baseline categories must be present
    for cat in ["work", "personal"]:
        assert cat in data["categories"], f"Expected category '{cat}' in {data['categories']}"

def test_put_categories_requires_json(creds, auth_headers):
    url = f"{creds['api_url']}/categories"
    resp = httpx.put(url, headers={**auth_headers, "Content-Type": "text/plain"}, content="raw string", timeout=10.0)
    assert resp.status_code in (400, 415)

def test_put_categories_validation_missing_key(creds, auth_headers):
    url = f"{creds['api_url']}/categories"
    resp = httpx.put(url, headers=auth_headers, json={"invalid_key": ["test"]}, timeout=10.0)
    assert resp.status_code == 400
    assert resp.json().get("status") == "error"

def test_put_categories_validation_non_list(creds, auth_headers):
    url = f"{creds['api_url']}/categories"
    resp = httpx.put(url, headers=auth_headers, json={"categories": "not a list"}, timeout=10.0)
    assert resp.status_code == 400
    assert resp.json().get("status") == "error"

def test_put_categories_validation_non_string_items(creds, auth_headers):
    url = f"{creds['api_url']}/categories"
    resp = httpx.put(url, headers=auth_headers, json={"categories": [123, False]}, timeout=10.0)
    assert resp.status_code == 400
    assert resp.json().get("status") == "error"
