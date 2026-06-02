# Purplle Store Intelligence

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the required dependencies:

```powershell
pip install -r requirements.txt
```

## Run The Backend

Start the FastAPI backend with:

```powershell
uvicorn app.main:app --reload
```

## Run The Frontend

Start the Streamlit frontend with:

```powershell
streamlit run dashboard\streamlit_app.py
```
