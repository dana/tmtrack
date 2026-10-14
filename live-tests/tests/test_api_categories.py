import httpx
import pytest

@pytest.fixture
def safe_categories_guard(creds, auth_headers):
    """
    Safely captures existing production categories before each test,
    ensures test assertions verify state invariance, and guarantees
    automatic restoration if anything ever modified the collection.
    """
    url = f"{creds['api_url']}/categories"
    resp = httpx.get(url, headers=auth_headers, timeout=10.0)
    assert resp.status_code == 200, f"Failed to fetch initial categories: {resp.text}"
    original_categories = resp.json().get("categories", [])
    assert isinstance(original_categories, list) and len(original_categories) > 0

    yield original_categories

    # Post-test verification and restoration guard
    verify_resp = httpx.get(url, headers=auth_headers, timeout=10.0)
    current_categories = verify_resp.json().get("categories", [])
    if current_categories != original_categories:
        restore_resp = httpx.put(url, headers=auth_headers, json={"categories": original_categories}, timeout=10.0)
        assert restore_resp.status_code == 200, f"Failed to restore original categories: {restore_resp.text}"


def test_get_categories_success(creds, auth_headers, safe_categories_guard):
    url = f"{creds['api_url']}/categories"
    resp = httpx.get(url, headers=auth_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data
    categories = data["categories"]
    assert isinstance(categories, list)
    assert len(categories) > 0
    # Every category must be a non-empty string
    assert all(isinstance(c, str) and len(c.strip()) > 0 for c in categories)


def test_put_categories_idempotent_safe_update(creds, auth_headers, safe_categories_guard):
    """Exercises PUT /categories happy path by safely submitting the existing categories."""
    url = f"{creds['api_url']}/categories"
    original = safe_categories_guard
    resp = httpx.put(url, headers=auth_headers, json={"categories": original}, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    assert data.get("message") == "Categories updated successfully."


def test_put_categories_requires_json(creds, auth_headers, safe_categories_guard):
    url = f"{creds['api_url']}/categories"
    resp = httpx.put(url, headers={**auth_headers, "Content-Type": "text/plain"}, content="raw string", timeout=10.0)
    assert resp.status_code in (400, 415)
    current = httpx.get(url, headers=auth_headers, timeout=10.0).json().get("categories")
    assert current == safe_categories_guard


def test_put_categories_validation_missing_key(creds, auth_headers, safe_categories_guard):
    url = f"{creds['api_url']}/categories"
    resp = httpx.put(url, headers=auth_headers, json={"invalid_key": ["test"]}, timeout=10.0)
    assert resp.status_code == 400
    assert resp.json().get("status") == "error"
    current = httpx.get(url, headers=auth_headers, timeout=10.0).json().get("categories")
    assert current == safe_categories_guard


def test_put_categories_validation_non_list(creds, auth_headers, safe_categories_guard):
    url = f"{creds['api_url']}/categories"
    resp = httpx.put(url, headers=auth_headers, json={"categories": "not a list"}, timeout=10.0)
    assert resp.status_code == 400
    assert resp.json().get("status") == "error"
    current = httpx.get(url, headers=auth_headers, timeout=10.0).json().get("categories")
    assert current == safe_categories_guard


def test_put_categories_validation_non_string_items(creds, auth_headers, safe_categories_guard):
    url = f"{creds['api_url']}/categories"
    resp = httpx.put(url, headers=auth_headers, json={"categories": [123, False]}, timeout=10.0)
    assert resp.status_code == 400
    assert resp.json().get("status") == "error"
    current = httpx.get(url, headers=auth_headers, timeout=10.0).json().get("categories")
    assert current == safe_categories_guard
