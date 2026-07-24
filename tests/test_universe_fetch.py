from __future__ import annotations

import requests
import pytest

from quant_lab.error import WikiFetchError
from quant_lab.sources.universe import fetch_sp500_universe


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_fetch_sp500_universe_returns_validated_members(monkeypatch):
    html = """
        <table>
            <thead>
                <tr><th>Symbol</th><th>Security</th><th>CIK</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>BRK.B</td>
                    <td>Berkshire Hathaway</td>
                    <td>1067983</td>
                </tr>
            </tbody>
        </table>
    """
    monkeypatch.setattr(
        "quant_lab.sources.universe.fetch.requests.get",
        lambda *args, **kwargs: FakeResponse(html),
    )

    result = fetch_sp500_universe()

    assert len(result) == 1
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
