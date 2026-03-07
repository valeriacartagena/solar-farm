# SolarSentinel AI

A high-fidelity minimum viable product (MVP) demonstration for a computer vision and satellite imagery drone inspection platform.

Built with React (Frontend) and FastAPI (Python Backend), augmented by Gemini LLM.

## Features

- **CV Mock Detections:** Jitters coordinates around a real location to simulate drone thermal fault detections.
- **Earth Engine Integration:** Retrieves satellite contextual imagery.
- **Gemini Synthetic Generator:** Calls a generative API for simulated training variants.
- **Interactive UI Dashboard:** React maps with animated stats charts.

## Run Instructions

### 1. Start the Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### 2. Start the Frontend

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to interact with the application.

## Env Configuration
Duplicate `backend/.env.example` as `backend/.env` to input real API keys. If keys are omitted or missing, the MVP graciously falls back to structured dummy responses perfectly suited for live Hackathon demonstrations!
