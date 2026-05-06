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
2. Start the supporting services using Docker Compose:
   ```bash
   docker-compose up -d
   ```
   This starts PostgreSQL and Redis. The backend and frontend are run locally during development.

3. Start the backend in a separate terminal:
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. Start the frontend in another terminal:
   ```bash
   cd frontend
   npm install
   npm start
   ```

### New Contributor Run Order
1. Start Docker with `docker-compose up -d`.
2. Start the backend server with Uvicorn.
3. Start the Expo frontend with `npm start`.

### Existing Developer Run Flow
If you already have the project cloned and dependencies installed, use this shorter flow:
1. Start the supporting services:
   ```bash
   docker-compose up -d
   ```
2. Start the backend from the `backend` directory:
   ```bash
   .venv\Scripts\Activate.ps1
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
3. Start the frontend from the `frontend` directory:
   ```bash
   npm start
   ```
4. Open the app and use the Ping Backend button to confirm the API is connected.

### Environment Variables and Secrets
1. Copy the template and create your local env file:
   ```bash
   cd backend
   copy .env.example .env
   ```
2. Add your real API keys in `backend/.env` (never in source code).
3. Keep `.env` uncommitted. The repository `.gitignore` already excludes env files.

### Module 1 and 2 Smoke Tests (Backend)
Run these after the backend API and Redis are running.

1. Health check:
   ```bash
   curl http://localhost:8000/api/health
   ```
2. Module 1 source collection:
   ```bash
   curl "http://localhost:8000/api/ingestion/collect/unstructured?limit_per_source=3"
   ```
3. Module 1 preprocessing:
   ```bash
   curl -X POST http://localhost:8000/api/ingestion/preprocess -H "Content-Type: application/json" -d "[{\"source\":\"mmda_twitter\",\"text\":\"Accident sa EDSA Ayala, mabigat ang traffic\",\"location_hint\":\"EDSA-Ayala\",\"timestamp\":\"2026-04-27T00:00:00Z\"}]"
   ```
4. Module 2 single verification:
   ```bash
   curl -X POST http://localhost:8000/api/nlp/verify -H "Content-Type: application/json" -d "{\"source\":\"mmda_twitter\",\"original_text\":\"Accident sa EDSA Ayala, mabigat ang traffic\",\"cleaned_text\":\"accident sa edsa ayala mabigat ang traffic\",\"language_hint\":\"taglish\",\"timestamp\":\"2026-04-27T00:00:00Z\",\"location_hint\":\"EDSA-Ayala\"}"
   ```
5. Module 2 evaluation metrics:
   ```bash
   curl -X POST http://localhost:8000/api/nlp/evaluate -H "Content-Type: application/json" -d "{\"threshold\":0.5,\"samples\":[{\"label\":1,\"score\":0.91},{\"label\":1,\"score\":0.75},{\"label\":0,\"score\":0.15},{\"label\":0,\"score\":0.40}]}"
   ```

### Spatial Mapping with OpenStreetMap (OSM)

This project includes Graph WaveNet-ready spatial grid generation using OpenStreetMap road network data. The spatial module enables flood-aware routing and traffic forecasting on real road networks.

#### Quick Start

1. **Ensure OSM data is available:**
   ```bash
   # The Philippines OSM data should be at:
   ml/data/raw/OSM/philippines-260503.osm.pbf
   # (~2.3 GB file from Geofabrik)
   ```

2. **Generate spatial grid (one-time setup):**
   From the repository root:
   ```bash
   cd ml
   ..\..\.venv\Scripts\Activate.ps1
   python scripts/generate_spatial_grid.py
   ```
   
   This creates:
   - `artifacts/spatial_grid/road_network_graph.pkl` - NetworkX MultiDiGraph
   - `artifacts/spatial_grid/adjacency_matrix.npz` - Sparse adjacency matrix for Graph WaveNet
   - `artifacts/spatial_grid/node_list.npy` - Node ID mappings
   - `artifacts/spatial_grid/metadata.json` - Grid statistics

3. **Test the integration:**
   ```bash
   python scripts/test_osm_integration.py
   ```
   
   This validates:
   - ✓ OSM graph extraction (nodes, edges, connectivity)
   - ✓ Adjacency matrix generation (sparsity, shape)
   - ✓ Flood hazard integration (if Project NOAH maps are present)
   - ✓ Flood-aware route optimization (if hazard maps available)

#### API Endpoints (Once Backend is Running)

**Generate spatial graph:**
```bash
curl -X POST http://localhost:8000/api/spatial/generate-graph \
  -H "Content-Type: application/json" \
  -d '{"pbf_path":"ml/data/raw/OSM/philippines-260503.osm.pbf","sparse":true}'
```

**Check spatial readiness:**
```bash
curl http://localhost:8000/api/spatial/status
```

**Assess flood risk at a location:**
```bash
curl -X POST http://localhost:8000/api/spatial/assess-place-risk \
  -H "Content-Type: application/json" \
  -d '{"longitude":121.5768,"latitude":14.6474,"rainfall_mm_per_hour":18.0}'
```

**Find flood-safe route:**
```bash
curl -X POST http://localhost:8000/api/spatial/reroute-with-hazard-avoidance \
  -H "Content-Type: application/json" \
  -d '{"origin":[120.98,14.60],"destination":[121.08,14.65],"rainfall_mm_per_hour":18.0}'
```

#### Downloading OSM Data

If the `.pbf` file is not present, download it:

```bash
# Option 1: Using wget (Linux/macOS)
cd ml/data/raw/OSM
wget https://download.geofabrik.de/asia/philippines-latest.osm.pbf

# Option 2: Using PowerShell (Windows)
$url = "https://download.geofabrik.de/asia/philippines-latest.osm.pbf"
$outPath = "ml\data\raw\OSM\philippines-latest.osm.pbf"
Invoke-WebRequest -Uri $url -OutFile $outPath

# Option 3: Manual download
# Visit: https://download.geofabrik.de/asia.html
# Download "Philippines" → place at ml/data/raw/OSM/
```

**Size:** ~2.3 GB (compressed). After extraction and processing, spatial grid artifacts total ~200-500 MB.

#### Architecture

The spatial module uses:
- **pyrosm** - Fast PBF parsing with bounding box filtering
- **NetworkX** - Road network graph representation (MultiDiGraph for parallel edges)
- **SciPy sparse** - Efficient adjacency matrix storage for Graph WaveNet input
- **GeoPandas** - Project NOAH flood hazard integration
- **Shapely** - Geometry operations for flood risk assessment

**Default Region:** Metro Manila (14.35°N-15.05°N, 120.88°E-121.08°E)

#### Graph Statistics (Metro Manila)

Expected output after `generate_spatial_grid.py`:
```
Nodes: ~55,000 (intersections, endpoints)
Edges: ~140,000 (road segments)
Sparsity: >99% (very sparse graph)
Adjacency matrix shape: (55000, 55000)
Artifacts total size: ~300 MB
```

#### Integration with ML Pipeline

Use in Graph WaveNet training:
```python
import pickle
import scipy.sparse as sp
import numpy as np

# Load spatial grid
G = pickle.load(open('artifacts/spatial_grid/road_network_graph.pkl', 'rb'))
A = sp.load_npz('artifacts/spatial_grid/adjacency_matrix.npz')
nodes = np.load('artifacts/spatial_grid/node_list.npy')

# A is a sparse matrix ready for:
# - Graph convolution layers (convert to dense if needed)
# - Spectral graph convolution
# - Message passing neural networks
```

#### Flood-Aware Routing (Optional)

If Project NOAH flood hazard shapefiles are available at `ml/data/raw/MetroManila/`:

```bash
python scripts/test_osm_integration.py
```

This tests flood risk assessment and finds safer alternate routes during heavy rainfall events.

### Local Development Setup

**Backend:**
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1  # On Windows PowerShell
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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