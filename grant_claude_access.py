#!/usr/bin/env python3
"""
Grant the Claude GitHub App access to a specific repository.

Usage:
    python grant_claude_access.py --token <your-github-pat> --repo voice-ai-intel

You need a GitHub Personal Access Token with these scopes:
  - read:user
  - write:packages (not needed, just needs basic user scope)
  - Actually just: user scope is enough to manage your own installations

Create one at: https://github.com/settings/tokens/new
Required scope: (no special scope needed for user installation management,
                 but 'repo' scope may be required if repo is private)
"""

import argparse
import json
import sys
import urllib.request
import urllib.error


def gh_api(path, token, method="GET", data=None):
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, headers=headers, method=method, data=body)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code} on {method} {path}: {body}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Grant Claude GitHub App access to a repo.")
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    parser.add_argument("--repo", default="voice-ai-intel", help="Repository name (default: voice-ai-intel)")
    parser.add_argument("--owner", default=None, help="GitHub username (auto-detected if omitted)")
    parser.add_argument("--app-slug", default="claude", help="GitHub App slug (default: claude)")
    args = parser.parse_args()

    # 1. Get authenticated user
    print("Fetching your GitHub identity...")
    user = gh_api("/user", args.token)
    if not user:
        sys.exit("Could not authenticate — check your token.")
    owner = args.owner or user["login"]
    print(f"  Authenticated as: {owner}")

    # 2. Get repo ID
    print(f"\nFetching repo info for {owner}/{args.repo}...")
    repo = gh_api(f"/repos/{owner}/{args.repo}", args.token)
    if not repo:
        sys.exit(f"Repo {owner}/{args.repo} not found or not accessible.")
    repo_id = repo["id"]
    print(f"  Repo ID: {repo_id}")

    # 3. Find the Claude app installation
    print(f"\nLooking for '{args.app_slug}' app installations on your account...")
    installations = gh_api("/user/installations", args.token)
    if installations is None:
        sys.exit("Could not list installations — make sure your token has the right scopes.")

    target = None
    for inst in installations.get("installations", []):
        slug = inst.get("app_slug", "")
        print(f"  Found app: {slug} (id={inst['id']})")
        if slug == args.app_slug:
            target = inst
            break

    if not target:
        print(f"\nApp '{args.app_slug}' is not installed on your account.")
        print("Install it first at: https://github.com/apps/claude")
        sys.exit(1)

    installation_id = target["id"]
    print(f"  Using installation ID: {installation_id}")

    # 4. Add repo to the installation
    print(f"\nAdding '{args.repo}' to the '{args.app_slug}' installation...")
    result = gh_api(
        f"/user/installations/{installation_id}/repositories/{repo_id}",
        args.token,
        method="PUT",
    )

    if result is not None:
        print(f"\nDone! '{args.repo}' is now accessible to the '{args.app_slug}' app.")
        print("Go back to your Claude Code session and retry the push.")
    else:
        print("\nSomething went wrong — see error above.")
        print("You can also do this manually:")
        print(f"  https://github.com/settings/installations/{installation_id}")


if __name__ == "__main__":
    main()
