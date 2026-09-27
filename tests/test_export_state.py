from unittest.mock import MagicMock, patch

from src.crunchyroll.models import SeriesSummary
from src.exporters.base import ExportResult
from src.main import _export_anilist
from src.storage.export_log import ExportLog
from src.storage.export_state import ExportState


def make_summary(series_id: str = "S1", max_episode: int = 1) -> SeriesSummary:
    return SeriesSummary(
        series_id=series_id,
        series_title=f"Anime {series_id}",
        max_episode=max_episode,
        first_watched_at="2026-01-01T00:00:00Z",
        last_watched_at="2026-01-02T00:00:00Z",
    )


def test_pending_includes_unexported_series(tmp_path):
    state = ExportState(tmp_path / "export_state.json")
    series = [make_summary()]

    assert state.pending("anilist", series) == series


def test_successfully_exported_series_is_skipped_until_it_changes(tmp_path):
    state = ExportState(tmp_path / "export_state.json")
    series = [make_summary()]
    state.record_successes("anilist", series, ["S1"])

    reloaded = ExportState(tmp_path / "export_state.json")
    assert reloaded.pending("anilist", series) == []

    changed = [make_summary(max_episode=2)]
    assert reloaded.pending("anilist", changed) == changed


def test_failed_series_remains_pending(tmp_path):
    state = ExportState(tmp_path / "export_state.json")
    series = [make_summary()]
    state.record_successes("anilist", series, [])

    assert state.pending("anilist", series) == series


def test_targets_track_export_state_independently(tmp_path):
    state = ExportState(tmp_path / "export_state.json")
    series = [make_summary()]
    state.record_successes("anilist", series, ["S1"])

    assert state.pending("anilist", series) == []
    assert state.pending("mal", series) == series


def test_anilist_export_only_sends_changed_series(tmp_path):
    state = ExportState(tmp_path / "export_state.json")
    unchanged = make_summary("S1")
    changed = make_summary("S2")
    state.record_successes("anilist", [unchanged], ["S1"])

    result = ExportResult()
    result.updated.append(changed.series_title)
    result.successful_series_ids.append(changed.series_id)
    exporter = MagicMock()
    exporter.export.return_value = result

    with patch("src.main.AniListExporter", return_value=exporter):
        _export_anilist(
            {"exporters": {"anilist": {"access_token": "token"}}},
            [unchanged, changed],
            ExportLog(tmp_path / "export_log.json"),
            state,
        )

    exporter.export.assert_called_once_with([changed])
    assert result.skipped == [unchanged.series_title]
