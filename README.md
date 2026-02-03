# MindPulse
AI-Powered Cognitive Burnout & Recovery Intelligence Platform.

MindPulse tracks mental overload and recovery capacity through a Mental Recovery Index (MRI), predicts burnout risk, and guides recovery with timed micro-interventions.

## Features
- Mental Recovery Index (MRI) with live sliders
- Burnout prediction + 7-day forecast
- Cognitive load timeline with intensity + hours
- Personalized recovery coach + timer flows
- Voice-enabled AI assistant (local rule-based)
- Daily check-in (mood, sleep, stress, workload, water)
- Simple demo auth (Gmail + username + password)

## Quick Start (Local)
### Backend
```cmd
cd backend
python -m pip install -r requirements.txt
python app.py
```

### Frontend
```cmd
cd frontend
python -m http.server 8000
```

Open: `http://localhost:8000`

## Auth Notes
- Demo auth is file-based and stored in `backend/users.json`.
- Do not commit `backend/users.json` to version control.
- A sample file is provided as `backend/users.sample.json`.

## Configuration
The frontend expects the API at:
```js
const API_BASE = "http://127.0.0.1:5050";
```
Update this if you deploy the backend elsewhere.

## Project Structure
```
frontend/
  index.html
backend/
  app.py
  requirements.txt
  users.sample.json
```

## Disclaimer
This is a prototype for demo and hackathon use. It is not medical advice.
