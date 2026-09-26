# Explicit ETF snapshot and superseded-anchor declaration

Date: 2026-09-07
as_of: 2026-09-04
ETF adjusted-close SHA256: 7b64be101f62166ed9261a8d51a8894f61310238dfa8d75c2c8e4f3d45c233e6

Authorized by Jaeyoung's September 7 instruction to pin and re-anchor honestly.
The pin is the currently available September 4 close, not an attempted recreation
of unavailable earlier downloads. Every research backtest is bounded inclusively
by data.as_of; live ingestion remains unbounded. Existing earlier study windows
(e.g. constituent panel ending June 30) remain earlier. Price files are unchanged.

Hash protocol and dimensions are in reports/etf-snapshot-2026-09-07/snapshot.json.
The content hash covers all configured ETF adj_close series from the configured
start through the pin; it detects historical adjustments even if the endpoint
is unchanged. Future journal entries from this task include as_of and this hash.

The 23 ETF anchors from the prior reproduction attempt are superseded, not
reproduced. The original raw inputs are unavailable. New anchors will be measured
under the pin and recorded next to the old values in a new journal entry; old
journal entries remain untouched. No parameter, cost, signal, or tolerance changes.
The ETF bar-count expectation is re-anchored from 5499 to the measured 5502 with
22 folds under this explicit snapshot. The old test failure is superseded by this
user-authorized input-boundary amendment, not suppressed.

The constituent run's reproduction prerequisite is withdrawn by the user.
No model has been fitted or new strategy result evaluated in this task.
