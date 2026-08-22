# Automated Manus Review Dispatch

## Purpose

This repository dispatches a private, isolated Manus review task after a qualifying push to `main`. The workflow attaches a compressed Git archive of the exact triggering commit, so the reviewer evaluates an immutable artifact rather than a branch label, commit message, or mutable working tree. It uses the Manus v2 asynchronous task-creation endpoint and a GitHub encrypted repository secret. [1] [2]

| Control | Boundary |
| --- | --- |
| Trigger | Substantive pushes to `main`, plus controlled manual dispatch. |
| Context | `git archive` of the exact `GITHUB_SHA`; oversized archives fail closed. |
| Credential | `MANUS_API_KEY` remains an encrypted GitHub Actions secret and is sent only as an API header. |
| Loop prevention | Review memos and the dispatcher file are ignored; a reviewer hand-off uses `[manus-review]`. |
| Write scope | A reviewer may create only `docs/MANUS_SPRINT85_REVIEW.md`, only after confirming GitHub write access. |

## Sprint 8.5 Review Contract

The task must read `docs/MANUS_SPRINT84_REVIEW.md`, extract the archive, and run the stated tests and type checks. Approval requires source and adversarial tests proving all of the following: raw-ledger bytes are parsed into an `AuditRun` or proven canonically identical to the submitted model; selected client and competitor evidence is `OPENED_VERIFIED`, snapshot-backed, tied to a real verifier run, and tied to immutable collection execution; and every promoted quote binds exact evidence ID, URL, snapshot digest, verifier-run ID, execution ID, and quote text.

Passing tests alone do not establish approval. The reviewer must attempt to falsify raw-ledger/model mismatch, missing snapshot, missing verifier run, missing execution provenance, optional quote snapshots, and altered quote provenance. A review memo is an engineering decision record, not proof of a commercial or causal claim.

## Operating Safeguards

If the secret is missing, archive exceeds the safe inline size, API response is unsuccessful, validation is incomplete, or GitHub write access is unavailable, the hand-off must stop without fabricating a review record. Revoke the Manus key and delete the repository secret if automation is disabled, access changes, or the credential could be exposed.

The first controlled exercise is the Sprint 8.5 implementation. Confirm that it runs the tests, creates an evidence-specific review memo, and changes only the permitted documentation file before treating the loop as operational.

## References

[1]: https://open.manus.ai/docs/v2/task.create "Manus API v2 task.create"
[2]: https://docs.github.com/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "GitHub Actions encrypted secrets"
