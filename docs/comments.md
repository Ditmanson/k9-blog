# Comments

Comments live in the `grizcomments` DynamoDB table (us-east-2) behind the AppSync API "griz.sh comments" (`3dlgu4u7cjg2pmp5zylj3zvcim`), both carried over from the old griz.sh. They're keyed by `postSlug`, the Post's URL path (ADR 0001).

## Policy: auto-approve + Turnstile

A Comment goes live as soon as it passes Turnstile. The `writeCommentToDynamo` AppSync function (`vky3llrbuff2nathtuzf7sjoeu`) sets `approved: true`, whatever the client sends. If spam gets through, change that to `false` with `aws appsync update-function`: new Comments then wait for approval.

`updateGrizcomments` and `deleteGrizcomments` reject every client call. Moderation only works with the owner's AWS credentials.

## Hide a Comment

```
scripts/hide-comment.py                            # list what's live
scripts/hide-comment.py <postSlug> <createdAt>     # hide one
```

Hidden is `approved: false`: the blog stops showing it. The public API can still return it to someone who queries without the filter, so delete anything that must be gone:

```
aws dynamodb delete-item --table-name grizcomments --region us-east-2 \
  --key '{"postSlug":{"S":"<postSlug>"},"createdAt":{"S":"<createdAt>"}}'
```

The table has no point-in-time recovery, so a delete is permanent.

## Approve hidden or pending Comments

```
cd scripts
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt   # once
./.venv/bin/python list-unapproved-comments.py    # writes pending-comments.yaml
./.venv/bin/python approve-comments.py            # pushes the ones flipped to approved: true
```

Neither needs a rebuild: Comments load in the browser.

## Keys

- **API key** (public, `commentsKey` in `hugo.yaml`): expires **2027-11-21**, and Comments stop working then. Extend it, up to 365 days out: `aws appsync update-api-key --api-id 3dlgu4u7cjg2pmp5zylj3zvcim --id <key> --expires <epoch seconds> --region us-east-2`
- **Turnstile secret**: only in the `verifyTurnstile` AppSync function. Never put it in git, issues, or logs. After rotating it in Cloudflare, update that function.
- **Turnstile hostnames**: the widget must allow every hostname the blog is served from, set in the Cloudflare dashboard.
