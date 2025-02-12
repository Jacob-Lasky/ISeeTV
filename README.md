<p align="center"><img src=https://github.com/user-attachments/assets/16ca67e4-b7ec-430b-82c5-65042506797d/></p>

<hr></hr>

The ISeeTV project seeks to build a docker-based IPTV client for desktop and mobile browsers. The spirit of the project is to be:
- Easy to use
- Easy to deploy
- Easy to contribute

## Planned Features:
<!-- START MILESTONES -->
### v1.0.0
| Milestone | Progress | # Issues Left |
|-----------|----------|--------------|
| [v1.0.0 Release - Other Tasks](https://github.com/Jacob-Lasky/ISeeTV/milestone/1) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/1?label=) | 7 |
| [Basic Mobile Functionality](https://github.com/Jacob-Lasky/ISeeTV/milestone/8) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/8?label=) | 3 |

### v2.0.0
| Milestone | Progress | # Issues Left |
|-----------|----------|--------------|
| [User Management](https://github.com/Jacob-Lasky/ISeeTV/milestone/2) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/2?label=) | 4 |
| [DVR Capabilities](https://github.com/Jacob-Lasky/ISeeTV/milestone/3) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/3?label=) | 2 |
| [v2.0.0 Release - Other Tasks](https://github.com/Jacob-Lasky/ISeeTV/milestone/4) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/4?label=) | 15 |
| [xTeVe-like filtering and restreaming](https://github.com/Jacob-Lasky/ISeeTV/milestone/5) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/5?label=) | 5 |
| [File-based themes and settings](https://github.com/Jacob-Lasky/ISeeTV/milestone/9) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/9?label=) | 1 |

<!-- END MILESTONES -->

## In-Progress issues
<!-- START TICKETS -->
| Title | Milestone |
|-------|-----------|
| [full screen video display, no need to have scrolling](https://github.com/Jacob-Lasky/ISeeTV/issues/87) | v1.0.0 - Mobile |
| [Fully expand sidebar](https://github.com/Jacob-Lasky/ISeeTV/issues/84) | v1.0.0 - Mobile |
<!-- END TICKETS -->

## Completed Features
<!-- START COMPLETED -->
| Milestone | Progress | # Issues Closed |
|-----------|----------|----------------|
| [v1.0.0 - EPG Parsing](https://github.com/Jacob-Lasky/ISeeTV/milestone/6) | ![Progress](https://img.shields.io/github/milestones/progress-percent/Jacob-Lasky/ISeeTV/6?label=&color=green) | 9 |

<!-- END COMPLETED -->




## Known Bugs
- When the EPG goes past the 12am mark (00:00), it counts upwards starting at 25. This is a limitation added by the Planby library. I will be transitioning out of this library but I wanted to get something working before I built my own EPG handler.

## Video UI:
![image](https://github.com/user-attachments/assets/2865d1f2-74fb-4cb6-9e2e-5043ef1c455e)

## Channel Picker:
![image](https://github.com/user-attachments/assets/3534c77d-3713-46b0-a55a-306a3984198f)
- Search box for channel searching
- Settings gear to bring up the settings modal
- Three channel tabs: All, Favorites and Recent
- Collapsable channel list
- Collapsable guide
- Count of channels and programs currently filtered

## Settings Modal:
![image](https://github.com/user-attachments/assets/a68129cd-17a4-4329-8c88-71d2de8cc7cc)
- Provide ISeeTV with an M3U link and (optionally) with an EPG link
- Change the update intervals
- Toggle to update links on start
- Change the theme to light, dark or system (default)
- Adjustable "recent" length
- Adjustable guide UI
- Automatic timezone recognition and able to be set by the user

## Help Modal:
![image](https://github.com/user-attachments/assets/78db3575-9d31-4280-9a85-e953cce9652a)
- Links to project pages
- Ability to hard reset all existing channels by wiping the database

## Channel and Guide Container:
![image](https://github.com/user-attachments/assets/8632aca1-0202-4c74-82d3-ffdec767bcef)
- live event indicator
- clickable events and channels

## Channel Modal:
![image](https://github.com/user-attachments/assets/7b9f74e2-78bc-47bc-a8f7-08dae437c80c)
- Detail view
- Can favorite from here
- Can watch channel from here

## Program Modal:
![image](https://github.com/user-attachments/assets/59d91a3b-33ea-4580-a084-04eaa8eb3bd6)
- Detail view including channel category and description
- Can watch program from here

## Running the project manually

1. Run `docker compose up` to start the containers.
2. Open `http://localhost:1313` in your browser.

## FAQ | Development | Feature Requests:
If you're thinking about contributing to this repo in any way, I want you to! I welcome all ideas, feedback, questions and PRs. I had never used React before starting this project and recognize how difficult it is to jump into something new. I want us all to support each other as we build cool things together.
- General Development Guidelines
  - Ask tons of questions
  - Keep code tested
  - Keep the README up to date


## Linting
- While in the frontend directory, run:
  - to check linting issues: `docker run --rm -v $(pwd):/app -w /app node:22 npm run lint`
    - to fix most linting issues: `docker run --rm -v $(pwd):/app -w /app node:22 npm run lint -- --fix`
- While in the backend directory, run:
  - check for type errors: `poetry run mypy .`
    - to fix most type errors, you'll need to manually edit the files
  - check for linting issues: `poetry run ruff check .`
    - to fix most linting issues: `poetry run ruff check . --fix`
  - check for formatting issues: `poetry run black --check .`
    - to fix most formatting issues: `poetry run black .`
