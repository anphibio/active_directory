from app.ad_client import paged_search


class FakeEntry:
    def __init__(self, payload):
        self.entry_attributes_as_dict = payload


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.entries = []
        self.result = {}

    def search(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            self.entries = [FakeEntry({"cn": "one"}), FakeEntry({"cn": "two"})]
            self.result = {
                "controls": {
                    "1.2.840.113556.1.4.319": {
                        "value": {
                            "cookie": b"next",
                        }
                    }
                }
            }
            return
        self.entries = [FakeEntry({"cn": "three"})]
        self.result = {
            "controls": {
                "1.2.840.113556.1.4.319": {
                    "value": {
                        "cookie": b"",
                    }
                }
            }
        }


def test_paged_search_collects_multiple_pages() -> None:
    connection = FakeConnection()

    entries = paged_search(
        connection,
        search_base="DC=example,DC=local",
        search_filter="(objectClass=*)",
        attributes=["cn"],
        limit=10,
        page_size=2,
    )

    assert entries == [{"cn": "one"}, {"cn": "two"}, {"cn": "three"}]
    assert len(connection.calls) == 2
    assert connection.calls[0]["paged_size"] == 2
    assert connection.calls[1]["paged_cookie"] == b"next"


def test_paged_search_respects_limit() -> None:
    connection = FakeConnection()

    entries = paged_search(
        connection,
        search_base="DC=example,DC=local",
        search_filter="(objectClass=*)",
        attributes=["cn"],
        limit=1,
        page_size=500,
    )

    assert entries == [{"cn": "one"}]
    assert len(connection.calls) == 1
    assert connection.calls[0]["paged_size"] == 1
