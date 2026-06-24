# AI Kanban Board

AI-powered Kanban board built with FastAPI, Next.js, React, Docker and SQLite.

## Features

* Secure authentication with session-based cookies
* SQLite persistence with Docker volumes
* AI-assisted board generation
* Drag-and-drop Kanban interface
* Multi-user support
* Dockerized deployment

## Tech Stack

**Frontend:** React, Next.js, TypeScript

**Backend:** FastAPI, SQLite

**DevOps:** Docker, Docker Compose

**AI:** OpenRouter

## Architecture

Frontend (Next.js) → FastAPI → SQLite → Docker Volume

## Running Locally

```bash
docker compose up --build
```

Application available at:

```text
http://localhost:8000
```

## Project Evolution

This project started from a frontend-only Kanban prototype and was extended into a full-stack application with authentication, persistence, AI integration, security hardening, and deployment support.
