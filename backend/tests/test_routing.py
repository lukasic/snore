import pytest
import os
from app.config import load_config, resolve_queue


@pytest.fixture(autouse=True)
def load_test_config():
    config_path = os.path.join(os.path.dirname(__file__), "test_config.yaml")
    load_config(config_path)


def test_no_match_falls_back_to_general():
    assert resolve_queue("icinga2", "linux-01", "SSH") == "general"


def test_host_pattern_routes_to_windows():
    assert resolve_queue("icinga2", "win-server-01", "WinRM") == "windows"


def test_non_matching_host_goes_to_general():
    assert resolve_queue("icinga2", "ubuntu-01", "HTTP") == "general"


def test_none_host_goes_to_general():
    assert resolve_queue("manual", None, None) == "general"
