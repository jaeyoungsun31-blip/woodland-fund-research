# Amendment — sealed multi-invocation execution

Date: 2026-09-08
Status: RECOMMENDED BY PLANNING — awaiting Jaeyoung's authorization
Amends: the "all four arms in one invocation, or none" clause of
`2026-09-08-xsmom-v16-dual-run-preregistration.md`
Cause: the execution environment terminated Codex A at a 30-second command
boundary before arm A completed.

## Nothing was contaminated

The artifacts under `reports/xsmom-v16-dual-run/arms/` are timestamped 02:56 and
all four carry `status: "refused"` with 16 trials — they are the stale output of
the earlier missing-price refusal. The terminated run wrote nothing. No OOS
number from any arm has been observed by anyone.

## Purpose versus mechanism

The clause exists to prevent seeing one arm's result and then deciding whether,
or how, to run the others — selective execution and selective reporting. It does
not exist to require a single operating-system process. Four arms over 6,736
dates, up to 950 columns and four cost levels cannot complete inside a 30-second
boundary, so the mechanism is now the blocker while the purpose is untouched.

## Decision

Execution may span multiple invocations. **Disclosure may not.**

1. Arms may be run in separate, resumable invocations, in any order.
2. **No arm's results may be read, summarized, logged, or reported while the run
   is incomplete** — not by an agent, not in a journal entry, not in a chat
   message. This is the binding clause.
3. A `run_id` is written at run start and stamped into every arm's output. A
   final `--report` step emits results only when all four arms carry completion
   markers **for the same run_id**, and re-verifies the frozen inputs (cleared
   subset, panel artifacts, anchor set) are unchanged from run start.
4. If any arm fails or is interrupted, **no report is emitted and no partial
   number is read.** The run is restarted or resumed; it is not partially
   reported.

## Required first step

`reports/xsmom-v16-dual-run/arms/dual-{A,B,C,D}/` already contain summaries from
the 02:56 refusal. A presence check would be satisfied by stale files. Those
directories must be cleared before the new run, and the completion check must
key on `run_id`, never on file existence alone.

## Why this is mechanics, not terms

Nothing about what is tested changes: same four arms, same frozen subset, same
window, same cost schedule, same gate, same quarantine. Only the process
boundary moves. The anti-selectivity guarantee is strengthened rather than
weakened, because it becomes an explicit sealed-report rule rather than an
implicit property of running one command.
