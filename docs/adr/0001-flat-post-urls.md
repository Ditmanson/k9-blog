# Flat Post URLs, Category as a taxonomy

Comments are keyed by the Post's URL path, so a Post that moves loses its Comments. Posts therefore live at `/posts/<slug>/` with Category as a one-per-Post taxonomy, rather than in a Hugo section per Category (`/gear/<slug>/`), so recategorizing never breaks links or Comments.

## Consequences

Renaming a published Post's slug still orphans its Comments. Don't, unless the Comments' `postSlug` values move with it.
