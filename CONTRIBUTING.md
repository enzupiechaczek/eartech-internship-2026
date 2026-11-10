# Contributing

## Branch flow
`feature/<name>-<taskID>-<short-name>` -> `team-x/sprint-N` -> `team-x/develop` -> `develop` -> `main`

Example: `feature/ali-3279-django-init`

- Team A (CourseHub) uses `team-a/*` branches. Team B (HealthPulse) uses `team-b/*` branches.
- Never push directly to `main`, `develop`, `team-x/develop` or `team-x/sprint-N`. Always open a pull request.
- Open your pull request into your team's current sprint branch (for example `team-a/sprint-1`).
- A teammate must review and approve your pull request before it is merged.
- The Scrum Master merges sprint branches into `team-x/develop`, then `develop`, then `main`.

## Project location
The CourseHub Django project lives in the `coursehub/` folder. Run `cd coursehub` before running `django-admin startproject coursehub .`.

## Secrets
Never commit `.env` files or secrets. Copy `coursehub/.env.example` to `coursehub/.env` and fill it in locally.

## Commit messages
Use short, clear messages and include the Azure Boards task ID, e.g. `feat: initialise Django project AB#3279`.
