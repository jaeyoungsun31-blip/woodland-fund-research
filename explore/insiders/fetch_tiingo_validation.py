"""Retired Tiingo fetch entry point: raw free-tier responses are not persisted."""


def fetch_all() -> None:
    """Refuse the superseded persistent-cache workflow."""
    raise RuntimeError("Tiingo raw-response caching is retired under the free-tier terms")


if __name__ == "__main__":
    fetch_all()
