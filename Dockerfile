# Frontend build stage
FROM node:20-slim AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run export

# Backend stage
FROM python:3.12-slim
WORKDIR /app

RUN pip install uv

COPY backend/pyproject.toml ./
RUN uv sync

# Copy backend source files used by FastAPI app.
COPY backend/*.py ./
COPY --from=frontend-build /app/out ./static

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]