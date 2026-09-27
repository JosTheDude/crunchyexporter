from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.crunchyroll.auth import CRAuthError
from src.main import _notify_notifleet, cli


def test_notify_notifleet_posts_failure_payload(monkeypatch):
    monkeypatch.setenv("NOTIFLEET_API_KEY", "test-key")
    response = MagicMock()

    with patch("src.main.requests.post", return_value=response) as post:
        _notify_notifleet(
            {
                "notifications": {
                    "notifleet": {
                        "url": "https://notifleet.jos.gg/",
                        "route": "personal",
                    }
                }
            },
            "CrunchyExporter sync failed",
            "Sync to anilist failed.",
        )

    post.assert_called_once_with(
        "https://notifleet.jos.gg/v1/notify",
        headers={"Authorization": "Bearer test-key"},
        json={
            "route": "personal",
            "title": "CrunchyExporter sync failed",
            "message": "Sync to anilist failed.",
        },
        timeout=10,
    )
    response.raise_for_status.assert_called_once()


def test_notify_notifleet_is_disabled_without_url(monkeypatch):
    monkeypatch.setenv("NOTIFLEET_API_KEY", "test-key")

    with patch("src.main.requests.post") as post:
        _notify_notifleet({}, "title", "message")

    post.assert_not_called()


def test_notify_notifleet_reads_key_from_file(tmp_path, monkeypatch):
    monkeypatch.delenv("NOTIFLEET_API_KEY", raising=False)
    key_file = tmp_path / "notifleet-api-key"
    key_file.write_text("file-key\n", encoding="utf-8")
    response = MagicMock()

    with patch("src.main.requests.post", return_value=response) as post:
        _notify_notifleet(
            {"notifications": {"notifleet": {"url": "https://notifleet.jos.gg", "api_key_file": str(key_file)}}},
            "title",
            "message",
        )

    assert post.call_args.kwargs["headers"] == {"Authorization": "Bearer file-key"}


def test_sync_notifies_when_crunchyroll_cookie_is_missing(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text(
        """\
notifications:
  notifleet:
    url: "https://notifleet.jos.gg"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("NOTIFLEET_API_KEY", "test-key")
    response = MagicMock()

    with patch("src.main.requests.post", return_value=response) as post:
        result = CliRunner().invoke(cli, ["-c", str(config), "sync", "--target", "anilist"])

    assert result.exit_code == 1
    post.assert_called_once()
    assert post.call_args.kwargs["json"]["title"] == "CrunchyExporter sync failed"


def test_sync_warns_when_crunchyroll_cookie_expires(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text(
        """\
crunchyroll:
  etp_rt: "expired-cookie"
notifications:
  notifleet:
    url: "https://notifleet.jos.gg"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("NOTIFLEET_API_KEY", "test-key")
    response = MagicMock()

    with patch("src.main.CRAuth.login_with_etp_rt", side_effect=CRAuthError("invalid_grant")), \
         patch("src.main.requests.post", return_value=response) as post:
        result = CliRunner().invoke(cli, ["-c", str(config), "sync", "--target", "anilist"])

    assert result.exit_code == 1
    assert post.call_args.kwargs["json"]["title"] == "Crunchyroll authentication needs attention"
