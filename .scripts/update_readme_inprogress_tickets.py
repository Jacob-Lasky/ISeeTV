import requests
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "Jacob-Lasky/ISeeTV"

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def get_inprogress_issues():
    """Fetch issues labeled 'inprogress' with their milestones."""
    url = f"https://api.github.com/repos/{REPO}/issues"
    params = {"labels": "inprogress", "state": "open"}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def update_readme(issues):
    """Update the README.md file with a table of issues sorted by milestone."""
    with open("README.md", "r") as file:
        content = file.readlines()

    start_marker = "<!-- START TICKETS -->\n"
    end_marker = "<!-- END TICKETS -->\n"
    start_index = content.index(start_marker) + 1
    end_index = content.index(end_marker)

    # Prepare issues sorted by milestone
    issues_with_milestones = sorted(
        issues, key=lambda issue: issue.get("milestone", {}).get("title", "") or "ZZZ"
    )

    # Build the new table content
    table = ["| Title | Milestone |\n", "|-------|-----------|\n"]
    for issue in issues_with_milestones:
        milestone = issue.get("milestone", {}).get(
            "title", "None"
        )  # Get milestone title or 'None'
        title = f"[{issue['title']}]({issue['html_url']})"
        table.append(f"| {title} | {milestone} |\n")

    # Replace content between markers
    content[start_index:end_index] = table

    # Write the updated README back to disk
    with open("README.md", "w") as file:
        file.writelines(content)


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        raise EnvironmentError(
            "GITHUB_TOKEN is not set. Ensure it is passed as an environment variable."
        )

    issues = get_inprogress_issues()
    update_readme(issues)
