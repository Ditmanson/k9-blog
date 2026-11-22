# Comments

Comments live in the `grizcomments` DynamoDB table (us-east-2) behind the AppSync API "griz.sh comments" (`3dlgu4u7cjg2pmp5zylj3zvcim`), both carried over from the old griz.sh. They're keyed by `postSlug`, the Post's URL path (ADR 0001).

## Policy: auto-approve + Turnstile

A Comment goes live as soon as it passes Turnstile. The `writeCommentToDynamo` AppSync function (`vky3llrbuff2nathtuzf7sjoeu`) sets `approved: true`, whatever the client sends. If spam gets through, change that to `false` with `aws appsync update-function`: new Comments then wait for approval. Before doing that, close the `onCreateGrizcomments` subscription: it sends every new Comment to anyone with the public key, approved or not.

`updateGrizcomments` and `deleteGrizcomments` reject every client call. Moderation only works with the owner's AWS credentials.

## Hide a Comment

```
scripts/hide-comment.py                            # list what's live
scripts/hide-comment.py <postSlug> <createdAt>     # hide one
```

Hidden is `approved: false`. The `listGrizcomments` and `getGrizcomments` resolvers only ever return approved Comments, whatever the client asks for, so a hidden one is readable only with the owner's AWS credentials. To remove one entirely:

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
