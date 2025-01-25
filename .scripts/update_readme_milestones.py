import requests
import os
import re

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "Jacob-Lasky/ISeeTV"
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def get_milestones():
    """Fetch all milestones from the repository."""
    url = f"https://api.github.com/repos/{REPO}/milestones"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def group_milestones_by_version(milestones):
    """Group milestones by their version prefix using regex."""
    version_groups = {}
    version_pattern = r"v(\d+\.\d+\.\d+)"

    for milestone in milestones:
        # Extract version from title (v1.0.0, v2.0.0, etc.)
        match = re.search(version_pattern, milestone["title"])
        if match:
            version = f"v{match.group(1)}"  # Add 'v' back to the version
            if version not in version_groups:
                version_groups[version] = []
            version_groups[version].append(milestone)

    return version_groups


def format_milestone_title(title):
    """Format milestone title by removing version prefix unless it's a Misc. Tasks or Other Tasks milestone."""
    if "Tasks" in title:  # Handles both "Misc. Tasks" and "Other Tasks"
        return title

    # Remove version prefix for other milestones
    # Matches "v1.0.0 - " or "v1.0.0 Release - "
    version_pattern = r"v\d+\.\d+\.\d+(?:\s+Release)?\s+-\s+"
    return re.sub(version_pattern, "", title)


def update_readme(milestones):
    """Update the README.md file with milestone tables grouped by version."""
    with open("README.md", "r") as file:
        content = file.readlines()

    start_marker = "<!-- START MILESTONES -->\n"
    end_marker = "<!-- END MILESTONES -->\n"
    start_index = content.index(start_marker) + 1
    end_index = content.index(end_marker)

    # Group milestones by version
    version_groups = group_milestones_by_version(milestones)

    # Build the new content
    new_content = []
    for version in sorted(version_groups.keys()):
        if version == "unknown":
            continue

        new_content.append(f"### {version}\n")
        new_content.append("| Milestone | Progress |\n")
        new_content.append("|-----------|----------|\n")

        for milestone in version_groups[version]:
            formatted_title = format_milestone_title(milestone["title"])
            progress_badge = f"![Progress](https://img.shields.io/github/milestones/progress-percent/{REPO}/{milestone['number']}?label=)"
            milestone_link = f"[{formatted_title}](https://github.com/{REPO}/milestone/{milestone['number']})"
            new_content.append(f"| {milestone_link} | {progress_badge} |\n")

        new_content.append("\n")  # Add blank line between versions

    # Replace content between markers
    content[start_index:end_index] = new_content

    # Write the updated README back to disk
    with open("README.md", "w") as file:
        file.writelines(content)


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        raise EnvironmentError(
            "GITHUB_TOKEN is not set. Ensure it is passed as an environment variable."
        )

    milestones = get_milestones()
    update_readme(milestones)
