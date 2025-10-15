# Quickstart: Operator Web Interface Development

**Feature**: Operator Web Interface
**Branch**: `004-smart-support-operator`
**Date**: 2025-10-15

## Purpose

This guide provides step-by-step instructions for setting up the development environment, running the operator web interface locally, and executing tests.

---

## Prerequisites

Before starting development, ensure you have:

- ✅ **Python 3.11+** installed (`python --version`)
- ✅ **Node.js 18+** installed (`node --version`)
- ✅ **npm 9+** installed (`npm --version`)
- ✅ **Git** installed (`git --version`)
- ✅ **Scibox API key** ([Get one here](https://llm.t1v.scibox.tech/))
- ✅ **Docker & Docker Compose** (for deployment testing)
- ✅ **Existing smart-support repository** cloned with working Classification and Retrieval modules

### Verify Existing Modules

```bash
# Ensure Classification Module works
python -m src.cli.classify "Как открыть счет?"

# Ensure Retrieval Module works
python -m src.cli.retrieve "Как открыть счет?" --category "Новые клиенты" --subcategory "Регистрация и онбординг"

# Verify embeddings database exists
ls -lh data/embeddings.db  # Should show ~1MB file
```

---

## Initial Setup

### Step 1: Create Feature Branch

```bash
# Checkout and pull latest main
git checkout main
git pull origin main

# Create feature branch
git checkout -b 004-smart-support-operator
```

### Step 2: Backend Setup

```bash
# Create backend directory structure
mkdir -p backend/src/api/routes
mkdir -p backend/tests/integration
mkdir -p backend/tests/unit

# Create Python package files
touch backend/src/__init__.py
touch backend/src/api/__init__.py
touch backend/src/api/routes/__init__.py
touch backend/tests/__init__.py
touch backend/tests/integration/__init__.py
touch backend/tests/unit/__init__.py

# Create backend requirements file
cat > backend/requirements.txt << 'EOF'
# FastAPI and ASGI server
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
pydantic==2.5.0

# CORS and middleware
python-json-logger==2.0.7

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.1
testcontainers==3.7.1
EOF

# Install backend dependencies (in project venv)
pip install -r backend/requirements.txt
```

### Step 3: Frontend Setup

```bash
# Create frontend using Vite
npm create vite@latest frontend -- --template react-ts

# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Install additional packages
npm install axios react-query @headlessui/react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Return to project root
cd ..
```

### Step 4: Configure Tailwind CSS

```bash
# Update frontend/tailwind.config.js
cat > frontend/tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF

# Update frontend/src/index.css
cat > frontend/src/index.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;
EOF
```

### Step 5: Environment Configuration

```bash
# Ensure .env exists in project root (from existing setup)
# Should already contain:
# SCIBOX_API_KEY=your_key_here
# FAQ_PATH=docs/smart_support_vtb_belarus_faq_final.xlsx

# Verify .env is in .gitignore
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore
```

---

## Running the Application

### Development Mode (Backend + Frontend)

**Terminal 1 - Backend Server:**

```bash
# From project root
cd backend

# Run FastAPI development server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process [12345] using WatchFiles
# INFO:     Application startup complete.
```

**Terminal 2 - Frontend Dev Server:**

```bash
# From project root
cd frontend

# Run Vite development server
npm run dev

# Expected output:
#   VITE v5.0.0  ready in 234 ms
#
#   ➜  Local:   http://localhost:5173/
#   ➜  Network: use --host to expose
```

**Access the Interface:**

Open browser to http://localhost:5173/

The frontend will proxy API requests to `http://localhost:8000` (configure in `vite.config.ts`).

---

## Testing

### Backend Unit Tests

```bash
# From project root
cd backend

# Run unit tests (fast, mocked)
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ -v --cov=src --cov-report=term-missing
```

### Backend Integration Tests

```bash
# From project root
cd backend

# Run integration tests (testcontainers - requires Docker running)
pytest tests/integration/ -v -m integration

# Test specific endpoint
pytest tests/integration/test_classification_api.py -v

# Test full workflow
pytest tests/integration/test_full_workflow.py -v
```

### Frontend Unit Tests

```bash
# From project root
cd frontend

# Run component tests
npm test

# With coverage
npm test -- --coverage
```

### End-to-End Tests

```bash
# From project root

# Ensure backend and frontend are running (see "Running the Application")
# Terminal 1: backend server
# Terminal 2: frontend server

# Terminal 3: Run E2E tests
pytest tests/e2e/ -v -m e2e

# Test specific user story
pytest tests/e2e/test_user_story_1.py -v
```

---

## API Documentation

Once the backend is running, view auto-generated API docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

Example API calls with curl:

```bash
# Health check
curl http://localhost:8000/api/health

# Classification
curl -X POST http://localhost:8000/api/classify \
  -H "Content-Type: application/json" \
  -d '{"inquiry": "Как открыть счет?"}'

# Retrieval
curl -X POST http://localhost:8000/api/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Как открыть счет?",
    "category": "Новые клиенты",
    "subcategory": "Регистрация и онбординг",
    "top_k": 5
  }'
```

---

## Docker Deployment

### Build and Run

```bash
# From project root

# Build Docker image (includes backend + frontend production build)
docker build -t smart-support-ui:latest -f Dockerfile.ui .

# Run with docker-compose
docker-compose up operator-ui

# Expected output:
# operator-ui_1  | INFO:     Uvicorn running on http://0.0.0.0:8000
# operator-ui_1  | INFO:     Application startup complete.

# Access at http://localhost:8080
```

### Stop Services

```bash
docker-compose down
```

---

## Project Structure (After Setup)

```
smart-support/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── main.py              # FastAPI app instance
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── classification.py # POST /api/classify
│   │   │   │   └── retrieval.py      # POST /api/retrieve
│   │   │   ├── models.py            # Pydantic request/response models
│   │   │   └── middleware.py        # CORS, logging, error handling
│   │   └── __init__.py
│   ├── tests/
│   │   ├── integration/
│   │   │   ├── test_classification_api.py
│   │   │   ├── test_retrieval_api.py
│   │   │   └── test_full_workflow.py
│   │   └── unit/
│   │       └── test_api_models.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── InquiryInput.tsx
│   │   │   ├── ClassificationDisplay.tsx
│   │   │   ├── TemplateList.tsx
│   │   │   ├── TemplateCard.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── ErrorMessage.tsx
│   │   │   └── ConfidenceBadge.tsx
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   ├── classification.ts
│   │   │   └── retrieval.ts
│   │   ├── types/
│   │   │   ├── classification.ts
│   │   │   └── retrieval.ts
│   │   ├── hooks/
│   │   │   └── useClipboard.ts
│   │   ├── App.tsx
│   │   ├── index.tsx
│   │   └── index.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── tests/
│   └── e2e/
│       ├── test_user_story_1.py
│       ├── test_user_story_2.py
│       └── test_edge_cases.py
│
├── specs/004-smart-support-operator/
│   ├── spec.md
│   ├── plan.md
│   ├── research.md
│   ├── data-model.md
│   ├── quickstart.md            # This file
│   └── contracts/
│       ├── classification-api.yaml
│       └── retrieval-api.yaml
│
└── docker-compose.yml            # Updated with operator-ui service
```

---

## Development Workflow

### 1. Implement a Feature

```bash
# Example: Add classification endpoint

# 1. Write API contract test first (TDD)
code backend/tests/integration/test_classification_api.py

# 2. Implement endpoint
code backend/src/api/routes/classification.py

# 3. Run test to verify
pytest backend/tests/integration/test_classification_api.py -v

# 4. Commit when green
git add backend/src/api/routes/classification.py backend/tests/integration/test_classification_api.py
git commit -m "Add classification endpoint (FR-002)"
```

### 2. Frontend Component Development

```bash
# Example: Add InquiryInput component

# 1. Create component file
code frontend/src/components/InquiryInput.tsx

# 2. Write component test
code frontend/src/components/__tests__/InquiryInput.test.tsx

# 3. Run test
cd frontend && npm test InquiryInput

# 4. Commit when complete
git add frontend/src/components/InquiryInput.tsx frontend/src/components/__tests__/InquiryInput.test.tsx
git commit -m "Add InquiryInput component (FR-001)"
```

### 3. Integration Testing

```bash
# After implementing backend endpoint + frontend component

# 1. Start backend + frontend servers
# Terminal 1: cd backend && uvicorn src.api.main:app --reload
# Terminal 2: cd frontend && npm run dev

# 2. Manual smoke test in browser (http://localhost:5173)

# 3. Write E2E test
code tests/e2e/test_user_story_1.py

# 4. Run E2E test
pytest tests/e2e/test_user_story_1.py -v

# 5. Commit when passing
git add tests/e2e/test_user_story_1.py
git commit -m "Add E2E test for user story 1 (P1)"
```

---

## Troubleshooting

### Backend Issues

**Problem**: `ImportError: No module named 'fastapi'`
**Solution**: Activate venv and reinstall dependencies
```bash
pip install -r backend/requirements.txt
```

**Problem**: `Classification service unavailable`
**Solution**: Verify SCIBOX_API_KEY is set
```bash
echo $SCIBOX_API_KEY  # Should show API key
# If empty, load .env:
export $(grep -v '^#' .env | xargs)
```

**Problem**: `FileNotFoundError: data/embeddings.db`
**Solution**: Populate embeddings database
```bash
./scripts/populate_database.sh --force
```

### Frontend Issues

**Problem**: `Cannot find module 'axios'`
**Solution**: Install dependencies
```bash
cd frontend && npm install
```

**Problem**: CORS error in browser console
**Solution**: Ensure backend CORS middleware is configured
```bash
# backend/src/api/main.py should include:
# app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], ...)
```

**Problem**: Tailwind styles not applying
**Solution**: Verify Tailwind configured correctly
```bash
# Check frontend/src/index.css has @tailwind directives
# Check frontend/tailwind.config.js content paths
```

### Docker Issues

**Problem**: `docker-compose up operator-ui` fails
**Solution**: Build image first
```bash
docker build -t smart-support-ui:latest -f Dockerfile.ui .
```

**Problem**: Port 8080 already in use
**Solution**: Stop conflicting service or change port
```bash
# Option 1: Find and kill process
lsof -ti:8080 | xargs kill

# Option 2: Change port in docker-compose.yml
# ports:
#   - "8081:8000"  # Use 8081 instead
```

---

## Performance Validation

### Check Classification Response Time

```bash
# Measure classification latency (should be <2000ms)
time curl -X POST http://localhost:8000/api/classify \
  -H "Content-Type: application/json" \
  -d '{"inquiry": "Как открыть счет?"}'

# Expected:
# {"inquiry":"Как открыть счет?","category":"...","processing_time_ms":1247,...}
# real    0m1.300s  # <2s ✅
```

### Check Retrieval Response Time

```bash
# Measure retrieval latency (should be <1000ms)
time curl -X POST http://localhost:8000/api/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query":"Как открыть счет?","category":"Новые клиенты","subcategory":"Регистрация и онбординг","top_k":5}'

# Expected:
# {"query":"...","results":[...],"processing_time_ms":487.3,...}
# real    0m0.550s  # <1s ✅
```

### Check Full Workflow Time

```bash
# Use E2E test with timing
pytest tests/e2e/test_user_story_1.py::test_full_workflow_under_10_seconds -v

# Should report: Full workflow completed in 3.2s ✅ (target: <10s)
```

---

## Next Steps

After completing setup:

1. **Read [tasks.md](./tasks.md)** (generated by `/speckit.tasks`) for step-by-step implementation
2. **Review [data-model.md](./data-model.md)** for entity definitions and validation rules
3. **Review [contracts/](./contracts/)** for OpenAPI specifications
4. **Start with backend** (FastAPI endpoints) before frontend
5. **Follow TDD** (tests first, then implementation)
6. **Commit frequently** (one feature = one commit)

---

## Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **React Documentation**: https://react.dev/
- **Tailwind CSS**: https://tailwindcss.com/docs
- **React Query**: https://tanstack.com/query/latest
- **Vite**: https://vitejs.dev/
- **pytest**: https://docs.pytest.org/
- **testcontainers**: https://testcontainers-python.readthedocs.io/
- **Chrome DevTools MCP**: (MCP tool documentation)

---

## Constitution Compliance Checklist

Before pushing code, verify:

- ✅ **Principle I**: Backend doesn't modify existing `src/classification/` or `src/retrieval/` modules
- ✅ **Principle II**: All user-facing messages are actionable (no technical jargon)
- ✅ **Principle III**: Integration tests use testcontainers, E2E tests use Chrome DevTools MCP
- ✅ **Principle IV**: API contracts match OpenAPI specs in `contracts/`
- ✅ **Principle V**: Docker deployment works with `docker-compose up operator-ui`
- ✅ **Principle VI**: No changes to `docs/smart_support_vtb_belarus_faq_final.xlsx`

---

**Ready to start implementation!** 🚀

Next command: `/speckit.tasks` (generate task breakdown from this plan)
