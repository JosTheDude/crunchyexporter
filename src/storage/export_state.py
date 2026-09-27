import hashlib
import json
from pathlib import Path

from src.crunchyroll.models import SeriesSummary
from .atomic import save_json


class ExportState:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"targets": {}}
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _fingerprint(series: SeriesSummary) -> str:
        payload = {
            "title": series.series_title,
            "max_episode": series.max_episode,
            "first_watched_at": series.first_watched_at,
            "last_watched_at": series.last_watched_at,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()

    def pending(self, target: str, series: list[SeriesSummary]) -> list[SeriesSummary]:
        exported = self._data.get("targets", {}).get(target, {})
        return [item for item in series if exported.get(item.series_id) != self._fingerprint(item)]

    def record_successes(self, target: str, series: list[SeriesSummary], successful_ids: list[str]) -> None:
        exported = self._data.setdefault("targets", {}).setdefault(target, {})
        successful = set(successful_ids)
        for item in series:
            if item.series_id in successful:
                exported[item.series_id] = self._fingerprint(item)
        save_json(self.path, self._data)
