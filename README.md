# 🚀 FastAPI WebSocket App

This is a FastAPI application with WebSocket support. It uses `uvicorn` as the ASGI server and enables hot reloading for development.

---

## 📦 Requirements

- Python 3.8+
- pip (Python package installer)
- Virtual environment (recommended)

---

## 🔧 Setup Instructions

### 1. Clone the repository

```bash
git clone <your-repo-url>
```
### 2. Navigate to the project directory
```bash
cd <your-project-directory>
```
### 3. Create and activate a virtual environment
```bash
python3 -m venv .venv
```
#### 4. Activate the virtual environment
```bash
source .venv/bin/activate
```
### 5. Install the required packages
```bash
pip install -r requirements.txt
```

### 🚀 Run the FastAPI App
To start the development server with hot reload and WebSocket support:

```bash
uvicorn app.main:app --reload --ws websockets
```

This assumes:

Your app's entry point is in app/main.py

Your FastAPI app instance is named app

🔁 The --reload flag enables auto-reload on code changes.
🔌 The --ws websockets flag explicitly sets WebSocket support using the websockets implementation.


### 🔌 WebSocket Usage
Once the server is running (default: http://127.0.0.1:8000), you can connect to your WebSocket endpoint using:

```
ws://127.0.0.1:8000/ws
```