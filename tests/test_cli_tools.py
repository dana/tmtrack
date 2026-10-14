import sys
from unittest.mock import patch
import pytest
import backup
import restore
import update_token


def test_backup_cli_main(tmp_path, mongodb_uri):
    """Test backup.py main() parses CLI args and invokes backup_database."""
    out_file = str(tmp_path / "cli_backup.json")
    test_args = ["backup.py", mongodb_uri, "tmtrack_test_db", out_file]
    with patch.object(sys, 'argv', test_args):
        backup.main()


def test_restore_cli_main_cancel(mongodb_uri, capsys):
    """Test restore.py main() when user enters 'no'."""
    test_args = ["restore.py", mongodb_uri, "tmtrack_test_db", "some_file.json"]
    with patch.object(sys, 'argv', test_args), patch('builtins.input', return_value='no'):
        restore.main()
    captured = capsys.readouterr()
    assert "cancelled by user" in captured.out


def test_restore_cli_main_confirm(mongodb_uri, tmp_path, capsys):
    """Test restore.py main() when user enters 'yes'."""
    dummy_file = tmp_path / "empty.json"
    dummy_file.write_text("{}")
    test_args = ["restore.py", mongodb_uri, "tmtrack_test_db", str(dummy_file)]
    with patch.object(sys, 'argv', test_args), patch('builtins.input', return_value='yes'):
        restore.main()
    captured = capsys.readouterr()
    assert "Database restore process completed" in captured.out


def test_update_token_cli_main(tmp_path, monkeypatch):
    """Test update_token.py main() CLI invocation."""
    import json
    test_file = tmp_path / "user_authentication.json"
    test_file.write_text(json.dumps([{"userid": "u1", "auth_token": "abc"}]))
    monkeypatch.chdir(tmp_path)
    
    test_args = ["update_token.py", "_suffix"]
    with patch.object(sys, 'argv', test_args):
        update_token.parser = update_token.argparse.ArgumentParser()
        update_token.parser.add_argument('token_part', type=str)
        args = update_token.parser.parse_args(['_suffix'])
        update_token.update_auth_token(args.token_part)
        
    updated = json.loads(test_file.read_text())
    assert updated[0]["auth_token"] == "abc_suffix"
