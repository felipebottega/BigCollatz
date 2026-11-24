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
