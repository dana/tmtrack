import json
import pytest
import update_token


def test_update_auth_token_success(tmp_path, monkeypatch):
    """Test update_auth_token appends the string to existing tokens."""
    test_auth_file = tmp_path / "user_authentication.json"
    initial_data = [
        {"userid": "user1", "auth_token": "tokenA"},
        {"userid": "user2", "auth_token": "tokenB"},
    ]
    with open(test_auth_file, "w") as f:
        json.dump(initial_data, f)

    # Change working directory so update_token operates on temp file
    monkeypatch.chdir(tmp_path)

    update_token.update_auth_token("_appended")

    with open(test_auth_file, "r") as f:
        updated = json.load(f)

    assert updated[0]["auth_token"] == "tokenA_appended"
    assert updated[1]["auth_token"] == "tokenB_appended"


def test_update_auth_token_file_not_found(tmp_path, monkeypatch, capsys):
    """Missing file is handled without throwing uncaught exceptions."""
    monkeypatch.chdir(tmp_path)
    update_token.update_auth_token("_test")
    captured = capsys.readouterr()
    assert "Error: user_authentication.json not found" in captured.out
