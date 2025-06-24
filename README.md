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

## Running the project manually
This is the standard way to run the project. It will build the frontend and backend and start the containers.

1. Run `docker compose up --build` to start the containers.
2. Open `http://localhost:1313` in your browser.

## Running the project in development mode
This enables hot reloading on the frontend and backend. It is not recommended for production use.

1. Run `docker compose -f docker-compose.dev.yml up --build` to start the containers.
2. Open `http://localhost:1313` in your browser.

## FAQ | Development | Feature Requests:
If you're thinking about contributing to this repo in any way, I want you to! I welcome all ideas, feedback, questions and PRs. I had never used Vite/Vue/Typescript before starting this project and recognize how difficult it is to jump into something new. I want us all to support each other as we build cool things together.
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
