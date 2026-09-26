"""Download SEC quarterly ownership ZIPs and retain code-P officer/director rows.

All downloads and outputs stay in explore/insiders. No return calculations.
"""

from __future__ import annotations

import io
import re
import time
import zipfile
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
INDEX = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
HEADERS = {"User-Agent": "Woodland Research research@example.org"}


def download(url: str) -> bytes:
    for attempt in range(5):
        try:
            response = requests.get(url, headers=HEADERS, timeout=120)
            response.raise_for_status()
            return response.content
        except requests.RequestException:
            if attempt == 4:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def read_table(archive: zipfile.ZipFile, filename: str, columns: list[str]) -> pd.DataFrame:
    with archive.open(filename) as handle:
        return pd.read_csv(
            handle,
            sep="\t",
            usecols=columns,
            dtype=str,
            encoding="utf-8-sig",
            low_memory=False,
        )


def main() -> None:
    index_file = HERE / "source.html"
    if not index_file.exists():
        index_file.write_bytes(download(INDEX))
    page = BeautifulSoup(index_file.read_text(), "html.parser")
    links = []
    for link in page.select('a[href*="form345.zip"]'):
        match = re.search(r"(20\d\d)q([1-4])_form345\.zip", link["href"])
        if match and int(match[1]) >= 2012:
            links.append((int(match[1]), int(match[2]), urljoin(INDEX, link["href"])))
    links.sort()
    frames = []
    sizes = []
    for year, quarter, url in links:
        target = HERE / f"{year}q{quarter}_form345.zip"
        if target.exists() and target.stat().st_size:
            content = target.read_bytes()
        else:
            content = download(url)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            transactions = read_table(
                archive,
                "NONDERIV_TRANS.tsv",
                [
                    "ACCESSION_NUMBER",
                    "NONDERIV_TRANS_SK",
                    "SECURITY_TITLE",
                    "TRANS_DATE",
                    "TRANS_CODE",
                    "TRANS_SHARES",
                    "TRANS_PRICEPERSHARE",
                    "TRANS_ACQUIRED_DISP_CD",
                ],
            )
            transactions = transactions.loc[
                (transactions.TRANS_CODE == "P") & (transactions.TRANS_ACQUIRED_DISP_CD == "A")
            ].copy()
            accessions = set(transactions.ACCESSION_NUMBER)
            if not accessions:
                continue
            submissions = read_table(
                archive,
                "SUBMISSION.tsv",
                [
                    "ACCESSION_NUMBER",
                    "FILING_DATE",
                    "DOCUMENT_TYPE",
                    "ISSUERCIK",
                    "ISSUERNAME",
                    "ISSUERTRADINGSYMBOL",
                ],
            )
            submissions = submissions.loc[
                submissions.ACCESSION_NUMBER.isin(accessions)
                & submissions.DOCUMENT_TYPE.isin(["4", "5"])
            ]
            owners = read_table(
                archive,
                "REPORTINGOWNER.tsv",
                [
                    "ACCESSION_NUMBER",
                    "RPTOWNERCIK",
                    "RPTOWNER_RELATIONSHIP",
                ],
            )
            owners = owners.loc[
                owners.ACCESSION_NUMBER.isin(accessions)
                & owners.RPTOWNER_RELATIONSHIP.fillna("").str.contains(
                    r"Officer|Director", case=False, regex=True
                )
            ]
            frame = transactions.merge(submissions, on="ACCESSION_NUMBER", how="inner")
            frame = frame.merge(owners, on="ACCESSION_NUMBER", how="inner")
            frame = frame.drop_duplicates(["ACCESSION_NUMBER", "NONDERIV_TRANS_SK", "RPTOWNERCIK"])
            frames.append(frame)
        sizes.append((year, quarter, url, len(content), len(frame)))
        target.unlink(missing_ok=True)
        print(f"{year} Q{quarter}: {len(frame)} rows, {len(content) / 1e6:.1f} MB", flush=True)
        time.sleep(0.2)
    events = pd.concat(frames, ignore_index=True)
    events.to_parquet(HERE / "sec_code_p_events.parquet", index=False)
    pd.DataFrame(
        sizes, columns=["year", "quarter", "source_url", "zip_bytes", "filtered_rows"]
    ).to_csv(HERE / "sec_quarters.csv", index=False)
    print(f"total={len(events)}, compressed_bytes={sum(row[3] for row in sizes)}")


if __name__ == "__main__":
    main()
