# Project Overview

This repo contains a small, end-to-end AI-assisted lending decisioning prototype, built with FastAPI (Python) on the backend and React + TypeScript + Vite on the frontend.

The application models a realistic consumer lending scenario where loan applications are submitted electronically and then manually decisioned by an underwriter (approve/decline). Using that historical data, the app:
 - Analyzes manually-decisioned applications to uncover patterns in key attributes (credit score, delinquencies, DTI, derogatories, etc.) that correlate strongly with approval or decline outcomes.
 - Synthesizes candidate decision rules (e.g. “3+ 30-day lates in the last 12 months → decline”, “score ≥ 820 and low DTI → usually approve”) along with simple support/confidence metrics.
 - Packages those rules into a candidate “decisioning profile” (rules + weights + score threshold) that can be saved and reused.
 - Runs the decision engine against applications using that profile, producing a score and approve/decline outcome per loan, and making it easy to compare system decisions vs historic manual decisions.

Under the hood, the backend is responsible for:
 - Storing and validating loan application data (as JSON).
 - Running a basic rule-mining routine to propose rules and a profile.
 - Evaluating applications against a profile using a scorecard-style rules engine.

The frontend provides:
 - A simple UI for loading and inspecting applications.
 - A workflow to run the rule miner, review candidate rules, and test the resulting profile by re-running decisions over the same dataset.

This project is **not** intended as a production credit decision engine. Its purpose is to explore how historical manually-decisioned loans can be used to derive transparent, rules-based decision logic and to provide a sandbox for experimenting with automated decisioning profiles.


## Future Work / Possible Enhancements

* **AI-informed rule discovery**  
Extend the rule-mining logic to incorporate LLM assistance in discovering and refining rules. For example, use an LLM to:
  - Propose interpretable rule conditions (with thresholds) that tend to support manually **approved** loans (positive contribution) or manually **declined** loans (negative contribution).
  - Suggest weight adjustments or rule combinations based on patterns found in the data.
  - Generate human-readable rationales that help risk teams understand why a candidate rule appears useful.

* **Interactive “chat with the applications” analysis**  
Add a dedicated chat view that allows a user to:
  - Select a subset (or full set) of applications and send them, as JSON, into an LLM context.
  - Ask open-ended questions like “Which attributes seem most predictive of approval?” or “What distinguishes borderline cases from clear declines?”
  - Iteratively explore the dataset through natural language, using the LLM as an “analysis assistant” to surface insights, hypotheses, and potential rule ideas.

* **Incorporating long-term performance and retrospective analysis**  
Enrich the dataset with **post-decision performance labels**, such as whether an approved loan went delinquent or defaulted within 12+ months. Potential extensions include:
  - Evaluating whether historically approved loans turned out to be “good” or “bad” decisions, and how proposed profiles would have changed that mix.
  - Performing retrospective analysis on **declined applications** (where subsequent credit behavior is known) to see how applicants’ risk profiles evolved after denial (e.g., improvement in score, reduction in delinquencies).
  - Using these performance insights to refine rules and profiles over time, aiming for not just alignment with manual decisions, but alignment with **actual loan outcomes**.


___

# Repository

This repository contains two applications that work together:

- api/ – Python backend API (served with Uvicorn, dependencies managed with uv)
- ui/ – React frontend (built and run with Node.js)

___

## Prerequisites

Make sure the following are installed on your system.

### Backend

- Python: version 3.13 (recommended)
- uv: Python project and dependency manager
  - Install uv using the official instructions from the uv documentation.
  - Verify installation by running:
    - uv --version

### Frontend

- Node.js: version 22.x (recommended)
  - Verify installation by running:
    - node --version
    - npm --version

### LLM

- LM Studio: Latest version (recommended)
- Download and load a model of your choosing (qwen/qwen3-vl-8b recommended)

___

## Backend (Python API – api/)

### 1. Install dependencies

From the repository root:

1. Change into the backend directory:
   - cd api
2. Sync and install backend dependencies:
   - uv sync

This will create or reuse a virtual environment for the project and install all backend dependencies defined in your pyproject.toml and uv.lock.

### 2. Run the API server

From within the api directory:

- Run the API server:
  - uv run uvicorn app.main:app

Notes:

- By default, Uvicorn listens on port 8000, so the API will be available at:
  - http://localhost:8000/
- If you want to be explicit about the port, you can use:
  - uv run uvicorn app.main:app --port 8000

Adjust the app.main:app reference if your ASGI app lives in a different module or file.

___

## Frontend (React UI – ui/)

### 1. Install dependencies

From the repository root:

1. Change into the frontend directory:
   - cd ui
2. Install frontend dependencies:
   - npm install

### 2. Run the frontend dev server

From within the ui directory:

- Start the development server:
  - npm run dev

By default, the dev server will be available at:

- http://localhost:5173/

Open that URL in your browser to view the app.

___

## LLM (LM Studio + Model) 

1. From LM Studio, go to Discover > Model Search (Ctrl+Shift+M)
2. Find a model that you can run on your machine.
3. Note: Model "qwen/qwen3-vl-8b" was used during development of this app.  If you choose a different model, either edit llm_client.py or set your LMSTUDIO_MODEL environment variable to specify the name of the different model.

___

## Typical Development Workflow

In two separate terminals:

### Terminal 1 – Backend

1. From the repo root: cd api
2. Install or update dependencies when needed: uv sync
3. Run the API server: uv run uvicorn app.main:app

### Terminal 2 – Frontend

1. From the repo root: cd ui
2. Install dependencies the first time: npm install
3. Run the frontend: npm run dev

Then visit http://localhost:5173 in your browser. The frontend will communicate with the backend running on http://localhost:8000.
