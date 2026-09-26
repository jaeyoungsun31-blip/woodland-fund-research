# Decision — admissibility of a date match as identity evidence

Date: 2026-09-06
Status: SIGNED 2026-09-06 (verbal, recorded — see A2 provenance note)
Extends: the citation-plus-corroboration protocol used in
`reports/security-resolver/2026-09-06-evidence-batch01/`

## The question Codex raised

Is an exact cited IPO or terminal-date match sufficient for an identity accept,
or must every acceptance also carry a numerical price fingerprint?

## Measurement

Across the 50,864 files in the store:

| | unique date | shared by >100 files |
|---|---:|---:|
| last bar | 2.9% | 37.0% |
| first bar | 3.1% | 13.2% |

`1997-12-31` is the first bar of **3,760 files**; `1999-01-04` of 1,546. These
are the vendor's history floor, not corporate events.

Of the 16 identity accepts in evidence-batch01, 15 rest on a date match alone,
with pivot-date multiplicities of 3 to 11. Two pairs collide exactly:

```
BBT_old / STI_old   both last bar 2019-12-06   (BB&T + SunTrust -> Truist)
APC_old / TMK       both last bar 2019-08-08
```

## Finding

Corporate actions cluster, and related companies exit on identical dates. Where
a pivot date is shared, the only thing separating the candidates is the ticker —
and the ticker is the channel the resolver exists not to trust. A date match
implied by the ticker match supplies no independent information; it is one
channel presented as two.

## Rule

Compute each pivot date's multiplicity from the manifest, then:

- **multiplicity 1** — a date match alone is sufficient.
- **multiplicity 2–3** — sufficient, recorded at medium confidence.
- **multiplicity 4 or more** — a numerical fingerprint is **required**. The
  citation must predict a number (terminal close against cited consideration,
  offering price, or a volume ratio) and the data must corroborate it.
- **`1997-12-31` and `1999-01-04` are never admissible as identity evidence**,
  at any multiplicity, in either direction.

Failing the numeric requirement is not a rejection. It returns the proposal to
`unknown` pending retrieval of a number from the citation already held.

## Reference row

`DOW_old` is the template: SEC filing cited, predicting last date 2017-08-31 AND
terminal close $66.65; observed 2017-08-31 at $66.65; agreement on both.

## Caveat — IPO first dates

First close is not the offering price; day-one returns of 10–30% are ordinary.
The numeric for an IPO vintage is the 424B4 offering price with an explicitly
stated tolerance band, or first-day volume against the subsequent median. Do not
impose a tight band the evidence cannot meet.
