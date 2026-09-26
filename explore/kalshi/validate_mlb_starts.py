"""Validate 200 deterministic rules-text MLB starts against the public MLB schedule."""

import json
import random
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from probe import ROOT

RULE = re.compile(
    r"If .+? wins the (.+?) professional baseball game originally scheduled for "
    r"([A-Za-z]+ \d{1,2}, \d{4}) at (\d{1,2}:\d{2}) (AM|PM) (EST|EDT),",
    re.I,
)
ALIASES = {
    "Arizona": "Arizona Diamondbacks",
    "Atlanta": "Atlanta Braves",
    "Baltimore": "Baltimore Orioles",
    "Boston": "Boston Red Sox",
    "Chicago C": "Chicago Cubs",
    "Chicago WS": "Chicago White Sox",
    "Cincinnati": "Cincinnati Reds",
    "Cleveland": "Cleveland Guardians",
    "Colorado": "Colorado Rockies",
    "Detroit": "Detroit Tigers",
    "Houston": "Houston Astros",
    "Kansas City": "Kansas City Royals",
    "Los Angeles A": "Los Angeles Angels",
    "Los Angeles D": "Los Angeles Dodgers",
    "Miami": "Miami Marlins",
    "Milwaukee": "Milwaukee Brewers",
    "Minnesota": "Minnesota Twins",
    "New York M": "New York Mets",
    "New York Y": "New York Yankees",
    "Oakland": "Athletics",
    "A's": "Athletics",
    "Athletics": "Athletics",
    "Philadelphia": "Philadelphia Phillies",
    "Pittsburgh": "Pittsburgh Pirates",
    "San Diego": "San Diego Padres",
    "San Francisco": "San Francisco Giants",
    "Seattle": "Seattle Mariners",
    "St. Louis": "St. Louis Cardinals",
    "Tampa Bay": "Tampa Bay Rays",
    "Texas": "Texas Rangers",
    "Toronto": "Toronto Blue Jays",
    "Washington": "Washington Nationals",
}
CACHE = ROOT / "mlb_schedule_cache"


def parse(row):
    match = RULE.search(row["rules_primary"] or "")
    if not match:
        return None
    matchup, date_text, clock, meridiem, suffix = match.groups()
    if " vs " not in matchup:
        return None
    away, home = matchup.split(" vs ", 1)
    home = re.sub(r"\s*\(Game \d+\)$", "", home)
    if away not in ALIASES or home not in ALIASES:
        return None
    local = datetime.strptime(f"{date_text} {clock} {meridiem}", "%b %d, %Y %I:%M %p")
    local = local.replace(tzinfo=ZoneInfo("America/New_York"))
    actual_suffix = local.strftime("%Z")
    if suffix.upper() != actual_suffix:
        return None
    return {
        "event": row["event"],
        "date": local.date().isoformat(),
        "kalshi_start_utc": local.astimezone(ZoneInfo("UTC")).isoformat(),
        "away": ALIASES[away],
        "home": ALIASES[home],
        "rules_primary": row["rules_primary"],
    }


def schedule(date):
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{date}.json"
    if path.exists():
        return json.loads(path.read_text())
    url = "https://statsapi.mlb.com/api/v1/schedule?" + urlencode({"sportId": 1, "date": date})
    with urlopen(
        Request(url, headers={"User-Agent": "kalshi-public-pilot/1.0"}), timeout=30
    ) as response:
        payload = json.load(response)
    path.write_text(json.dumps(payload) + "\n")
    return payload


def main():
    rows = [
        json.loads(line)
        for line in (ROOT / "sports_metadata/KXMLBGAME.jsonl").read_text().splitlines()
    ]
    events = {row["event"]: row for row in rows if row["result"] in ("yes", "no")}
    parsed = [x for x in (parse(row) for row in events.values()) if x]
    sample = random.Random(20260923).sample(parsed, 200)
    comparisons = []
    for index, item in enumerate(sample, 1):
        candidates = []
        # A game near midnight UTC can appear on either neighbouring UTC date.
        for offset in (-1, 0, 1):
            date = (
                (datetime.fromisoformat(item["date"]) + timedelta(days=offset)).date().isoformat()
            )
            for day in schedule(date).get("dates", []):
                for game in day.get("games", []):
                    if (
                        game["teams"]["away"]["team"]["name"] == item["away"]
                        and game["teams"]["home"]["team"]["name"] == item["home"]
                    ):
                        candidates.append(game)
        start = datetime.fromisoformat(item["kalshi_start_utc"])
        matched = (
            min(
                candidates,
                key=lambda game: abs(
                    datetime.fromisoformat(game["gameDate"].replace("Z", "+00:00")) - start
                ),
            )
            if candidates
            else None
        )
        delta = (
            (
                datetime.fromisoformat(matched["gameDate"].replace("Z", "+00:00")) - start
            ).total_seconds()
            / 60
            if matched
            else None
        )
        comparisons.append(
            {
                **item,
                "official_start_utc": matched["gameDate"] if matched else None,
                "official_status": matched["status"]["detailedState"] if matched else None,
                "delta_minutes": delta,
                "within_15_minutes": delta is not None and abs(delta) <= 15,
            }
        )
        if index % 50 == 0:
            print(f"validated {index}/200", flush=True)
    output = {
        "sample_seed": 20260923,
        "sample_size": len(sample),
        "parsed_events": len(parsed),
        "within_15_minutes": sum(row["within_15_minutes"] for row in comparisons),
        "mismatches": [row for row in comparisons if not row["within_15_minutes"]],
        "comparisons": comparisons,
    }
    (ROOT / "mlb_start_validation.json").write_text(json.dumps(output, indent=2) + "\n")
    print(
        output["within_15_minutes"],
        "/",
        len(sample),
        "match; mismatches",
        len(output["mismatches"]),
    )


if __name__ == "__main__":
    main()
