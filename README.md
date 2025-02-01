<p align="center"><img src=https://github.com/user-attachments/assets/16ca67e4-b7ec-430b-82c5-65042506797d/></p>

<hr></hr>

The ISeeTV project seeks to build a docker-based IPTV client for desktop and mobile browsers. The spirit of the project is to be:
- Easy to use
- Easy to deploy
- Easy to contribute

## Planned Features:
<!-- START MILESTONES -->
### v1.0.0
| Milestone | Progress |
|-----------|----------|
| [v1.0.0 Release - Other Tasks](https://github.com/Jacob-Lasky/ISeeTV/milestone/1) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/1?label=) |
| [EPG Parsing](https://github.com/Jacob-Lasky/ISeeTV/milestone/6) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/6?label=) |

### v2.0.0
| Milestone | Progress |
|-----------|----------|
| [User Management](https://github.com/Jacob-Lasky/ISeeTV/milestone/2) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/2?label=) |
| [DVR Capabilities](https://github.com/Jacob-Lasky/ISeeTV/milestone/3) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/3?label=) |
| [v2.0.0 Release - Other Tasks](https://github.com/Jacob-Lasky/ISeeTV/milestone/4) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/4?label=) |
| [xTeVe-like filtering and restreaming](https://github.com/Jacob-Lasky/ISeeTV/milestone/5) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/5?label=) |

<!-- END MILESTONES -->

## In-Progress issues
<!-- START TICKETS -->
| Title | Milestone |
|-------|-----------|
| [EPG visualization](https://github.com/Jacob-Lasky/ISeeTV/issues/52) | v1.0.0 - EPG Parsing |
| [Guide view via expanded scrolling element ](https://github.com/Jacob-Lasky/ISeeTV/issues/30) | v1.0.0 - EPG Parsing |
<!-- END TICKETS -->

## UI:
![image](https://github.com/user-attachments/assets/30fffa09-fbca-45a5-a6ef-4c3c6ff2907b)
- Three channel tabs: All, Favorites and Recent
- Collapsable channel list
- Search box
- Settings gear to bring up the settings modal
- Toggleable channel numbers
-   Channel search appears when channel numbers are toggled

## Settings Modal:
![image](https://github.com/user-attachments/assets/56c695d2-434d-4109-9be3-8f4717bb367f)
- Provide ISeeTV with an M3U link and (optionally) with an EPG link
- Change the update interval
- Set the M3U to update on app-startup
- Change the theme to light, dark or system (default)

## Running the project manually

1. Run `docker compose up` to start the containers.
2. Open `http://localhost:1313` in your browser.

## FAQ | Development | Feature Requests:
If you're thinking about contributing to this repo in any way, I want you to! I welcome all ideas, feedback, questions and PRs. I had never used React before starting this project and recognize how difficult it is to jump into something new. I want us all to support each other as we build cool things together.
- General Development Guidelines
  - Ask tons of questions
  - Keep code tested
  - Keep the README up to date
