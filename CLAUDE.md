## Agent skills

### Issue tracker

Issues and specs live as GitHub Issues on `Ditmanson/k9-blog`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context layout (`GLOSSARY.md` + `docs/adr/` at the repo root). See `docs/agents/domain.md`.

## Project

K9-Communication LLC's Blog: the casual dog blog that replaces griz.sh on that domain. Companion to the business site in `../caninecommunication` (k9-communication.com), whose stack and theme it shares.

## Workflow

- Until cutover to griz.sh, push freely. After cutover a push deploys the live blog: push only when the owner says so.
- Leave `../griz` and live griz.sh alone until cutover.
- Seed and drafted Posts are published under the owner's name: use only facts from the owner's own content, never invent anecdotes.
- **Test before committing:** `python3 -m unittest discover tests` (needs Hugo, `sass` on PATH, and `npm ci`), plus a visual check at phone width (~390px).
- Test-driven: failing test, then the change.
- Comments and their moderation: `docs/comments.md`. Hosting: `docs/deploys.md`.

## New content inbox

`newcontent.md` (repo root, untracked) is the owner's scratch inbox for new Posts (notes, video links, rough copy). When told to "review the new content":

1. Read `newcontent.md`; if unclear, ask before building.
2. Create or edit Posts in `content/posts/`: one Category, any Tags, today's date, light edits to the owner's words only.
3. Run the tests and check the build.
4. When the owner says we're done, reset the inbox with `echo > newcontent.md`. Never reset before then.
