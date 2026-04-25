# Event-Aware-Traffic-Forecasting

Welcome to the Event-Aware Traffic Forecasting project! This guide contains instructions for setting up the project, our technology stack, and guidelines for contributing.

## Tech Stack

### Backend
- **Framework:** Python, FastAPI
- **Database:** PostgreSQL (with PostGIS/GeoAlchemy2 for spatial data), AsyncPG
- **Caching/Queue:** Redis
- **Server:** Uvicorn

### Frontend
- **Framework:** React Native (Expo)
- **Styling:** TailwindCSS
- **Language:** TypeScript

### Infrastructure
- **Containerization:** Docker & Docker Compose

## Setup and Run Instructions

### Prerequisites
- Docker and Docker Compose
- Node.js and npm (for frontend local development)
- Python 3.12+ (for backend local development)

### Running with Docker (Recommended)
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Event-Aware-Traffic-Forecasting
   ```
2. Start the services using Docker Compose:
   ```bash
   docker-compose up --build
   ```
   This will spin up the backend API, frontend environment, database, and Redis.

### Local Development Setup

**Backend:**
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

**Frontend:**
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Expo development server:
   ```bash
   npm start
   ```

## Contributor Guide

We welcome contributions! Please adhere to the following guidelines when contributing to the project.

### Branch Naming Conventions
Always create a new branch for your work. Use the following format:
`<type>/<short-description>`

Types:
- `feature/` - For new features or enhancements
- `bugfix/` - For fixing bugs
- `hotfix/` - For urgent fixes
- `docs/` - For documentation updates
- `chore/` - For maintenance tasks (e.g., dependency updates)

Example: `feature/add-traffic-map-component`

### Commit Message Standards
We follow Conventional Commits. Each commit message should be structured as follows:

```
<type>(<scope>): <subject>
```

- **type:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`
- **scope:** (optional) The module or component being changed (e.g., `api`, `auth`, `ui`).
- **subject:** A short, imperative tense description of the change (e.g., `add user authentication`).

Example: `feat(api): add endpoint for historical traffic data`

### Pull Requests
1. Ensure your branch is up to date with the `main` branch.
2. Verify that your changes run locally without errors.
3. Open a Pull Request (PR) with a clear title and description of your changes.
4. Request reviews from other maintainers.

## Future Testing Standards
As the project grows, we will be enforcing comprehensive testing standards. Contributors should prepare to:
- Write unit tests for new backend logic and endpoints using `pytest`.
- Provide component and integration tests for the React Native frontend using tools like `Jest` and `React Native Testing Library`.
- Ensure new code passes all CI/CD linting and testing pipelines before merging.
- **Test Coverage:** All new features must include corresponding test cases, aiming to maintain or improve overall project coverage.