from __future__ import annotations

from quant_lab.sources.universe import SP500UniverseMember
from quant_lab.storage import UniverseLoadResult


def test_sync_universe_fetches_once_and_writes_selected_target(monkeypatch):
    from quant_lab.pipeline import load_universe

    members = [
        SP500UniverseMember(
            ticker="AAPL",
            company_name="Apple Inc.",
            cik="320193",
        )
    ]
    expected = UniverseLoadResult(
        target="postgres",
        received=1,
        inserted=1,
        updated=0,
        unchanged=0,
        deleted=0,
    )
    calls = []

    monkeypatch.setattr(
        load_universe,
        "fetch_sp500_universe",
        lambda: members,
    )

    def fake_load(received_members, *, target):
        calls.append((received_members, target))
        return expected

    monkeypatch.setattr(
        load_universe,
        "load_sp500_universe",
        fake_load,
    )

    result = load_universe.sync_sp500_universe(target="postgres")

    assert result == expected
    assert calls == [(members, "postgres")]
