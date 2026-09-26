from pathlib import Path

from woodland.live.alpaca import PaperClient, write_snapshot


class Response:
    def __init__(self, value):
        self.value = value

    def raise_for_status(self):
        pass

    def json(self):
        return self.value


class Session:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if "quotes" in url:
            return Response({"quotes": {"SPY": {"bp": 1}}})
        return Response([] if url.endswith(("/positions", "/orders")) else {"status": "ACTIVE"})


def test_snapshot_is_read_only_and_includes_iex_quotes(tmp_path: Path):
    session = Session()
    snapshot = PaperClient("key", "secret", session).snapshot(["SPY"])
    assert snapshot["mode"] == "paper-read-only" and snapshot["feed"] == "iex"
    assert snapshot["quotes"]["SPY"]["bp"] == 1
    assert all(call[1]["headers"]["APCA-API-KEY-ID"] == "key" for call in session.calls)
    path = write_snapshot(snapshot, tmp_path)
    assert path.exists() and path.read_text().endswith("\n")
