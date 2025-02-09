import requests
import os
import re
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "Jacob-Lasky/ISeeTV"
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def get_milestones():
    """Fetch all milestones from the repository."""
    url = f"https://api.github.com/repos/{REPO}/milestones?state=all"
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


def update_readme_for_open_milestones(milestones):
    """Update the README.md file with milestone tables grouped by version."""
    with open("README.md", "r") as file:
        content = file.readlines()

    # Update milestones section
    open_start_index = content.index("<!-- START MILESTONES -->\n") + 1
    open_end_index = content.index("<!-- END MILESTONES -->\n")

    # Group milestones by version
    version_groups = group_milestones_by_version(milestones)

    # Build the milestones content
    open_milestones_content = []

    for version in sorted(version_groups.keys()):
        logger.info(f"Processing version: {version}")
        if version == "unknown":
            continue

        open_milestones_content.append(f"### {version}\n")
        open_milestones_content.append("| Milestone | Progress |\n")
        open_milestones_content.append("|-----------|----------|\n")

        for milestone in version_groups[version]:
            logger.info(f"Processing milestone: {milestone['title']}")
            if milestone["state"] == "open":
                logger.info(f"- Milestone is open")
                formatted_title = format_milestone_title(milestone["title"])
                progress_badge = f"![Progress](https://img.shields.io/github/milestones/progress-percent/{REPO}/{milestone['number']}?label=)"
                milestone_link = f"[{formatted_title}](https://github.com/{REPO}/milestone/{milestone['number']})"
                open_milestones_content.append(
                    f"| {milestone_link} | {progress_badge} |\n"
                )

        open_milestones_content.append("\n")
    # Replace milestones content
    logger.info(f"Updating milestones content")
    content[open_start_index:open_end_index] = open_milestones_content


def update_readme_for_completed_milestones(milestones):
    """Update the README.md file with milestone tables grouped by version."""
    with open("README.md", "r") as file:
        content = file.readlines()

    # Update milestones section
    completed_start_index = content.index("<!-- START COMPLETED -->\n") + 1
    completed_end_index = content.index("<!-- END COMPLETED -->\n")

    closed_milestones_content = []

    # don't want version labels in the closed milestones content
    closed_milestones_content.append("| Milestone | Progress |\n")
    closed_milestones_content.append("|-----------|----------|\n")

    for milestone in milestones:
        if milestone["state"] == "closed":
            logger.info(f"- Milestone is closed")
            progress_badge = f"![Progress](https://img.shields.io/github/milestones/progress-percent/{REPO}/{milestone['number']}?label=&color=green)"
            milestone_link = f"[{milestone['title']}](https://github.com/{REPO}/milestone/{milestone['number']})"
            closed_milestones_content.append(
                f"| {milestone_link} | {progress_badge} |\n"
            )

    closed_milestones_content.append("\n")

    content[completed_start_index:completed_end_index] = closed_milestones_content
    # Write the updated README back to disk
    with open("README.md", "w") as file:
        file.writelines(content)


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        raise EnvironmentError(
            "GITHUB_TOKEN is not set. Ensure it is passed as an environment variable."
        )

    milestones = get_milestones()
    update_readme_for_open_milestones(milestones)
    update_readme_for_completed_milestones(milestones)
