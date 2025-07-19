<p align="center"><img src=https://github.com/user-attachments/assets/16ca67e4-b7ec-430b-82c5-65042506797d/></p>

<hr></hr>

The ISeeTV project seeks to build a docker-based IPTV proxy and filtering-client for desktop and mobile browsers. The spirit of the project is to be:
- Easy to use
- Easy to deploy
- Easy to contribute

## Project Roadmap
Check out the project roadmap here:
- https://github.com/users/Jacob-Lasky/projects/6/views/1

# Guide and Channel proxy
## Major Features
- [x] Strong foundational database design
- [x] UI for managing IPTV streams
- [x] Explorable inital M3U, filtered M3U and final M3U
- [ ] Easily editable final M3U
- [ ] Powerful built-in filters for creating M3U playlists
- [ ] Plugin-based filters for ever more fine-tuned refining of playlists

## Running the project manually
This is the standard way to run the project. It will build the frontend and backend and start the containers.

1. Run `docker compose up --build` to start the containers.
2. Open `http://localhost:1313` in your browser.

## Running the project in development mode
This enables hot reloading on the frontend and backend. It is not recommended for production use.

1. Run `docker compose -f docker-compose.dev.yml up --build` to start the containers.
2. Open `http://localhost:1313` in your browser.

Once running, API documentation can be found at `http://localhost:1314/docs`.

## FAQ | Development | Feature Requests:
If you're thinking about contributing to this repo in any way, I want you to! I welcome all ideas, feedback, questions and PRs. I had never used Vite/Vue/Typescript before starting this project and recognize how difficult it is to jump into something new. I want us all to support each other as we build cool things together.
- General Development Guidelines
  - Ask tons of questions
  - Keep code tested
  - Keep the README up to date


## Linting
- While in the frontend directory, run:
    - to check linting issues: `pnpm run format-and-lint` (or, if you want to containerize pnpm: `docker run --rm -v $(pwd):/app -w /app node:22-slim pnpm run format-and-lint`)
    - to fix most linting issues: `pnpm run format-and-lint -- --fix` (or, if you want to containerize pnpm: `docker run --rm -v $(pwd):/app -w /app node:22-slim pnpm run format-and-lint -- --fix`)
- While in the backend directory, run:
    - to format: `uv run ruff format .` (or, if you want to containerize uv: `docker run --rm -v $(pwd):/app -w /app python:3.11-slim uv run ruff format .`)
    - to fix most linting issues: `uv run ruff check . --fix` (or, if you want to containerize uv: `docker run --rm -v $(pwd):/app -w /app python:3.11-slim uv run ruff check . --fix`)
    - to check for type errors: `uv run pyright .` (or, if you want to containerize uv: `docker run --rm -v $(pwd):/app -w /app python:3.11-slim uv run pyright .`)
    - to fix most type errors, you'll need to manually edit the files
