"""
Fetches merged PRs by a GitHub user across all public repos
and updates the README with a dynamic Open Source Contributions section.
"""

import os
import re
import json
import urllib.request
import urllib.error
from datetime import datetime

GITHUB_USERNAME = "aayushbaluni"
README_PATH = os.path.join(os.path.dirname(__file__), "..", "README.md")
START_MARKER = "<!-- CONTRIBUTIONS:START -->"
END_MARKER = "<!-- CONTRIBUTIONS:END -->"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
MIN_STARS = 100


def github_api(url: str) -> tuple[list | dict, dict]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": GITHUB_USERNAME}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        resp_headers = dict(resp.headers)
    return data, resp_headers


def fetch_merged_prs() -> list[dict]:
    prs = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/search/issues?"
            f"q=author:{GITHUB_USERNAME}+type:pr+is:merged+-user:{GITHUB_USERNAME}"
            f"&sort=updated&order=desc&per_page=100&page={page}"
        )
        try:
            data, _ = github_api(url)
        except urllib.error.HTTPError as e:
            print(f"API error: {e.code} {e.reason}")
            break
        items = data.get("items", [])
        if not items:
            break
        for item in items:
            repo_url = item.get("repository_url", "")
            repo_name = "/".join(repo_url.split("/")[-2:]) if repo_url else "unknown"
            prs.append({
                "title": item["title"],
                "url": item["html_url"],
                "repo": repo_name,
                "repo_url": f"https://github.com/{repo_name}",
                "merged_at": item.get("pull_request", {}).get("merged_at", item.get("closed_at", "")),
                "number": item["number"],
            })
        if len(items) < 100:
            break
        page += 1
    return prs


def get_repo_stars(repo: str) -> int:
    try:
        data, _ = github_api(f"https://api.github.com/repos/{repo}")
        return data.get("stargazers_count", 0)
    except urllib.error.HTTPError:
        return 0


def format_stars(count: int) -> str:
    if count >= 1000:
        return f"{count / 1000:.1f}k"
    return str(count)


def build_section(prs: list[dict]) -> str:
    if not prs:
        return "_No merged PRs found yet. Check back soon!_"

    repo_groups: dict[str, list[dict]] = {}
    for pr in prs:
        repo_groups.setdefault(pr["repo"], []).append(pr)

    repos_with_stars = []
    for repo, repo_prs in repo_groups.items():
        stars = get_repo_stars(repo)
        if stars >= MIN_STARS:
            repos_with_stars.append((repo, repo_prs, stars))
    repos_with_stars.sort(key=lambda x: x[2], reverse=True)

    if not repos_with_stars:
        return "_No merged PRs in repos with 100+ stars yet. Check back soon!_"

    lines = []
    total_prs = sum(len(rp) for _, rp, _ in repos_with_stars)
    total_repos = len(repos_with_stars)
    lines.append(
        f"Merged PRs across **{total_repos} open-source repositories** "
        f"— **{total_prs} contributions** and counting.\n"
    )

    lines.append("| Repository | Stars | PRs | Recent Contribution |")
    lines.append("|------------|-------|-----|---------------------|")

    for repo, repo_prs, stars in repos_with_stars:
        repo_short = repo.split("/")[-1]
        stars_display = format_stars(stars)
        pr_count = len(repo_prs)
        latest = repo_prs[0]
        pr_link = f"[#{latest['number']}]({latest['url']})"
        title = latest["title"]
        if len(title) > 60:
            title = title[:57] + "..."
        lines.append(
            f"| [**{repo_short}**]({repo_prs[0]['repo_url']}) "
            f"| ⭐ {stars_display} "
            f"| {pr_count} "
            f"| {pr_link} — {title} |"
        )

    return "\n".join(lines)


def update_readme(section_content: str) -> None:
    with open(README_PATH, "r") as f:
        readme = f.read()

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )

    if pattern.search(readme):
        new_readme = pattern.sub(
            f"{START_MARKER}\n{section_content}\n{END_MARKER}",
            readme,
        )
    else:
        print(f"Markers not found in README. Add {START_MARKER} and {END_MARKER} to your README.md")
        return

    with open(README_PATH, "w") as f:
        f.write(new_readme)

    print(f"README updated with {len(section_content)} chars of contribution data.")


def main() -> None:
    print(f"Fetching merged PRs for {GITHUB_USERNAME}...")
    prs = fetch_merged_prs()
    print(f"Found {len(prs)} merged PRs across {len(set(pr['repo'] for pr in prs))} repos.")
    section = build_section(prs)
    update_readme(section)


if __name__ == "__main__":
    main()
