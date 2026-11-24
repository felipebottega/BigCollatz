# BigCollatz repository instructions

Write the README as a standalone description of the project's present purpose,
capabilities, usage, and limitations. Keep implementation history, version
comparisons, changelog entries, and descriptions of improvements in
conversation with the maintainer. Cite mathematical sources where relevant.

## Starting a new task

Use the existing BigCollatz checkout when available. If there is no checkout,
clone `https://github.com/felipebottega/BigCollatz.git`.

Before starting new work, check the current branch and local changes with
`git status -sb`, then run `git fetch origin main`. Base new work on
`origin/main` unless the user specifies a branch or asks to continue work
already in progress. Preserve local edits and commits when switching bases.

## Project objective

BigCollatz must be able to verify giant Collatz cycles exactly, at the scale
permitted by the mathematical lower bounds for nontrivial cycles. Sampling
and scores guide the search. A cycle verdict must follow from an exact
certificate or exact arithmetic.

Review any change that restricts the search or verifier to small inputs.
Distinguish necessary mathematical bounds and user-selected sampling budgets
from implementation shortcuts and the resources of the current machine.
A speedup or compressed representation must preserve the exact meaning of
the word it verifies. State which large-scale paths were actually tested.
