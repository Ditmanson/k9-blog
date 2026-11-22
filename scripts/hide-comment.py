#!/usr/bin/env python3
"""List the live comments, or hide one (approved:false) by its postSlug and createdAt."""

import argparse
import json
import subprocess
import sys

TABLE_NAME = "grizcomments"
REGION = "us-east-2"


def aws(*args):
    result = subprocess.run(
        ["aws", "dynamodb", *args, "--table-name", TABLE_NAME, "--region", REGION, "--output", "json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"aws dynamodb {args[0]} failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout) if result.stdout.strip() else {}


def list_live():
    items = aws(
        "scan",
        "--filter-expression", "approved = :true",
        "--expression-attribute-values", '{":true":{"BOOL":true}}',
    )["Items"]
    for c in sorted(items, key=lambda c: c["createdAt"]["S"]):
        # repr, so a comment can't put control characters in the terminal
        print(f"{c['postSlug']['S']!r} {c['createdAt']['S']}  "
              f"[{c['name']['S']!r}] {c['comment']['S'][:60]!r}")
    print(f"{len(items)} live comment(s)")


def hide(post_slug, created_at):
    aws(
        "update-item",
        "--key", json.dumps({"postSlug": {"S": post_slug}, "createdAt": {"S": created_at}}),
        "--update-expression", "SET approved = :false",
        # else a typo creates a blank comment
        "--condition-expression", "attribute_exists(postSlug)",
        "--expression-attribute-values", '{":false":{"BOOL":false}}',
    )
    print(f"hidden: {post_slug} @ {created_at}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("post_slug", nargs="?", help="e.g. /posts/griz/")
    parser.add_argument("created_at", nargs="?", help="as printed by the listing")
    args = parser.parse_args()
    if args.post_slug is None:
        list_live()
    elif args.created_at is None:
        parser.error("hiding needs both post_slug and created_at")
    else:
        hide(args.post_slug, args.created_at)


if __name__ == "__main__":
    main()
