from __future__ import annotations

import requests
import pytest
import pandas as pd

from quant_lab.error import WikiFetchError
from quant_lab.sources.universe import fetch_sp500_universe


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_fetch_sp500_universe_returns_validated_members(monkeypatch):
    monkeypatch.setattr(
        "quant_lab.sources.universe.fetch.requests.get",
        lambda *args, **kwargs: FakeResponse("<table></table>"),
    )
    table = pd.DataFrame(
        {
            "Symbol": ["BRK.B", *[f"T{i:03}" for i in range(399)]],
            "Security": [
                "Berkshire Hathaway",
                *[f"Test Company {i}" for i in range(399)],
            ],
            "CIK": ["1067983", *[str(i + 1) for i in range(399)]],
        }
    )
    monkeypatch.setattr(
        "quant_lab.sources.universe.fetch.pd.read_html",
        lambda *args, **kwargs: [table],
    )

    result = fetch_sp500_universe()

    assert len(result) == 400
    assert result[0].ticker == "BRK-B"
    assert result[0].company_name == "Berkshire Hathaway"
    assert result[0].cik == "0001067983"


def test_fetch_sp500_universe_rejects_changed_page_shape(monkeypatch):
    html = """
        <table>
            <thead><tr><th>Unexpected</th></tr></thead>
            <tbody><tr><td>value</td></tr></tbody>
        </table>
    """
    monkeypatch.setattr(
        "quant_lab.sources.universe.fetch.requests.get",
        lambda *args, **kwargs: FakeResponse(html),
    )

    with pytest.raises(WikiFetchError, match="缺少必要字段"):
        fetch_sp500_universe()


def test_fetch_sp500_universe_translates_network_errors(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(
        "quant_lab.sources.universe.fetch.requests.get",
        fail,
    )

    with pytest.raises(WikiFetchError, match="维基百科请求失败") as exc_info:
        fetch_sp500_universe()

    assert isinstance(exc_info.value.__cause__, requests.Timeout)


def test_fetch_sp500_universe_rejects_partial_invalid_snapshot(monkeypatch):
    monkeypatch.setattr(
        "quant_lab.sources.universe.fetch.requests.get",
        lambda *args, **kwargs: FakeResponse("<table></table>"),
    )
    table = pd.DataFrame(
        {
            "Symbol": [f"T{i:03}" for i in range(400)],
            "Security": [
                " " if i == 17 else f"Test Company {i}"
                for i in range(400)
            ],
            "CIK": [str(i + 1) for i in range(400)],
        }
    )
    monkeypatch.setattr(
        "quant_lab.sources.universe.fetch.pd.read_html",
        lambda *args, **kwargs: [table],
    )

    with pytest.raises(WikiFetchError, match="第 17 行校验失败"):
        fetch_sp500_universe()


def test_fetch_sp500_universe_rejects_implausibly_small_snapshot(
    monkeypatch,
):
    monkeypatch.setattr(
        "quant_lab.sources.universe.fetch.requests.get",
        lambda *args, **kwargs: FakeResponse("<table></table>"),
    )
    table = pd.DataFrame(
        {
            "Symbol": ["AAPL"],
            "Security": ["Apple Inc."],
            "CIK": ["320193"],
        }
    )
    monkeypatch.setattr(
        "quant_lab.sources.universe.fetch.pd.read_html",
        lambda *args, **kwargs: [table],
    )

    with pytest.raises(WikiFetchError, match="数量异常"):
        fetch_sp500_universe()
