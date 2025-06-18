<p align="center"><img src=https://github.com/user-attachments/assets/16ca67e4-b7ec-430b-82c5-65042506797d/></p>

<hr></hr>

The ISeeTV project seeks to build a docker-based IPTV proxy and client for desktop and mobile browsers. The spirit of the project is to be:
- Easy to use
- Easy to deploy
- Easy to contribute

## Project Roadmap
Check out the project roadmap here:
- https://github.com/users/Jacob-Lasky/projects/6/views/1

# Guide and Channel proxy
## Major Focus
As I've continued working on this project, I realize that I'm working on two distinct features; an EPG/M3U proxy similar to xTeVe and a video-player. The aspect that is missing from other proxies is that TV is dynamic and program-based. Sure, channels can be an important indicator of my interest in the show. BBC always has news playing, ESPN always has sports playing. But what if I want to watch a top-25 NCAA football or basketball matchup? It might be playing on my local news station, on ESPN, CBS or even some channel I've never seen. I want to be able to filter the channels I reveal to an IPTV player based on a channel name or a program name. And I want to do this dynamically so that my guide is 'on demand' and easy to scroll through instead of full of fluff that simply adds noise.

Today, my focus is on fleshing out the proxy while maintaining ISeeTV's spirit of ease. My plans for this phase of the project are on the roadmap but broadly can be broken down into the following pieces:
- [ ] Strong foundational database design
- [ ] UI for managing IPTV streams
- [ ] Powerful built-in filters for creating M3U playlists
- [ ] Plugin-based filters for ever more fine-tuned refining of playlists
- [ ] Easily editable final M3U
- [ ] Explorable inital M3U, filtered M3U and final M3U

As an aside, the video player is a much more difficult challenge and there are tons of different tools that do this well - although not as a self-hosted client, which is why I still see value in that side of the project.

# Video Player and UI
The development of this is currently on hold as I flesh out the M3U proxy. The video player works. It isn't beautiful and is loaded with bugs. But it's in an MVP for my purposes!

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
