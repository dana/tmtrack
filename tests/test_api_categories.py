import json
import pytest
from tests.conftest import (
    DANA_HEADERS,
    MICHELLE_HEADERS,
    DANA_GROUPS,
    assert_auth_info,
)


def test_get_categories_empty_initially(client):
    """When no categories document exists, returns empty list."""
    response = client.get('/api/v1/categories', headers=DANA_HEADERS)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert_auth_info(data, "dana", DANA_GROUPS)
    assert data["categories"] == []


def test_put_categories_non_json(client):
    """Non-JSON request to PUT /categories returns 400 or 415."""
    response = client.put(
        '/api/v1/categories',
        data="not json",
        content_type='text/plain',
        headers=DANA_HEADERS
    )
    assert response.status_code in (400, 415)


def test_put_categories_missing_categories_key(client):
    """PUT without 'categories' key in JSON returns 400."""
    response = client.put(
        '/api/v1/categories',
        json={"items": ["work"]},
        headers=DANA_HEADERS
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "'categories' key" in data["message"]


def test_put_categories_not_a_list(client):
    """PUT with 'categories' as a non-list returns 400."""
    response = client.put(
        '/api/v1/categories',
        json={"categories": "work,personal"},
        headers=DANA_HEADERS
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "must be a list" in data["message"]


def test_put_categories_elements_not_strings(client):
    """PUT with 'categories' containing non-strings returns 400."""
    response = client.put(
        '/api/v1/categories',
        json={"categories": ["work", 123, "personal"]},
        headers=DANA_HEADERS
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "must be strings" in data["message"]


def test_put_and_get_categories_lifecycle(client):
    """PUT updates categories and subsequent GET returns the new list."""
    new_categories = ["Engineering", "Design", "DevOps", "Break"]
    put_resp = client.put(
        '/api/v1/categories',
        json={"categories": new_categories},
        headers=DANA_HEADERS
    )
    assert put_resp.status_code == 200
    put_data = json.loads(put_resp.data)
    assert put_data["status"] == "success"
    assert "Categories updated successfully" in put_data["message"]

    get_resp = client.get('/api/v1/categories', headers=MICHELLE_HEADERS)
    assert get_resp.status_code == 200
    get_data = json.loads(get_resp.data)
    assert get_data["categories"] == new_categories
