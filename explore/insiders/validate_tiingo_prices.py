"""Retired raw Tiingo analysis; only derived validation tables are retained."""


def analyze() -> None:
    """Refuse a rerun that would require the deleted raw responses."""
    raise RuntimeError("Tiingo raw responses were deleted under the free-tier terms")


if __name__ == "__main__":
    analyze()
