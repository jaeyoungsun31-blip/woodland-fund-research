# 2026-09-04 — Phase 4 turnover-accounting correction

Append-only implementation record. Not a study and not a revision of prior
cycle journals.

The planning review `2026-09-04-planning-review-turnover-accounting-defect.md`
identified that the broker could submit orders after the no-trade band reported
zero turnover. This fix makes the live broker apply the declared band once,
against current paper exposure, and execute only the resulting boundary order.

Current exposure now includes both `/positions` and outstanding `/orders`:
unfilled buys increase expected holdings and unfilled sells reduce them before
new quantities are calculated. This prevents a subsequent cycle from sizing a
duplicate order while the first remains open.

For a paper-submission cycle, the journal now reports realized one-cycle
turnover as the sum of newly submitted order notionals divided by the account
equity used for sizing. It also retains the bounded-target turnover as a
separately labelled reference figure; the two are not interchangeable. The
realized annualized figure is derived from the submitted turnover.

Paper execution cost figures remain lower bounds: paper fills omit impact,
latency slippage, queue position, price improvement, fees, and liquidity
constraints; IEX quoted spreads have an upward bias relative to the
consolidated quote.

Regression coverage verifies an inside-band live drift submits no order and
reports zero turnover; an outside-band drift moves only to the band boundary;
reported turnover equals submitted notional divided by equity; and an
unfilled open order suppresses a duplicate submission.
