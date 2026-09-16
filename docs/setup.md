# DietAI24 Local Setup & Installation Guide

This guide walks you through setting up and running DietAI24 on your machine (Windows, macOS, or Linux).

---

## Prerequisites

- **Python:** 3.10 to 3.14
- **Node.js:** 18+ (tested on Node v24)
- **Git**

---

## 1. Backend Setup

### Navigate to the repository
```bash
cd indian-food-calorie-estimator
```

### Install Backend Dependencies
```bash
python -m pip install -r backend/requirements.txt
```

> **Note on PyTorch / CPU:** PyTorch will run smoothly on CPU. No GPU or CUDA configuration is required.

### Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp backend/.env.example backend/.env
# On Windows PowerShell:
Copy-Item backend/.env.example backend/.env
```

By default, `VISION_MODE=mock` is enabled, which allows you to run and demo the full app without needing an API key.

If you have an Anthropic API key and want to use real Claude 3.5 Sonnet vision:
```env
VISION_MODE=claude
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### Build the FAISS Index
The database and embeddings can be built in one command:
```bash
python scripts/build_index.py
```
This generates:
- `data/faiss_index.bin`
- `data/food_embeddings.npy`
- `data/food_id_order.json`

### Run Backend Server
```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

---

## 2. Frontend Setup

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend Vite dev server will start at:
- **Application URL:** [http://localhost:5173](http://localhost:5173)

All API calls from `localhost:5173` are automatically proxied to the backend at `localhost:8000`.

---

## 3. Running Automated Tests

Run the full pytest suite from the project root:
```bash
python -m pytest tests -v
```

This verifies:
- Calculator formulas and BMR/TDEE arithmetic (`test_calculator.py`)
- Database loading and queries (`test_database.py`)
- Food normalization and alias matching (`test_normalizer.py`)
- FAISS vector retriever and confidence scoring (`test_retriever.py`)
- FastAPI endpoints `/health`, `/foods`, `/analyze`, and `/recalculate` (`test_api.py`)
