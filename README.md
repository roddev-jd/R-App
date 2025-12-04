# SUITE Gateway

## Overview

`SUITE Gateway` is a **FastAPI** based central gateway that aggregates a collection of design‑tool utilities and auxiliary services under a single web server. It provides:

- A unified entry point (`/`) that serves the main `index.html` UI.
- Static asset serving for the FlexStart UI, manuals, data files and tool‑specific HTML front‑ends.
- A set of **REST APIs** for:
  - Health checking (`/health`).
  - Birthday management (`/api/birthdays/*`).
  - System capability discovery (`/api/system/capabilities`).
  - Asynchronous execution of internal Python scripts (`/api/run-script`).
  - Downloading tool directories as ZIP archives (`/api/download-tool/{script_id}`).
- Dynamic integration of two sub‑applications (`reportes` and `prod_peru`) that are mounted under `/reportes` and `/prod_peru` respectively.
- Centralised logging and error handling.

## Main Features

| Feature | Description |
|---|---|
| **FastAPI gateway** | Single FastAPI app that routes requests to static files, sub‑apps and custom endpoints. |
| **Static routes** | Serves assets, manuals, data and tool HTML pages (`/assets_flexstart`, `/manuales`, `/data`, `/herramientas`). |
| **Birthday API** | Endpoints to retrieve birthdays for the current month, all months, or a specific month, reading from `data/birthdays.json`. |
| **System capabilities** | Returns a JSON object indicating availability of optional components (DuckDB, OpenCV, reportes, ahead‑tool). |
| **Script execution** | Allows clients to launch any permitted design‑tool script asynchronously via `/api/run-script`. |
| **Tool download** | Packages a tool’s folder into a ZIP and streams it to the client via `/api/download-tool/{script_id}`. |
| **Sub‑application integration** | Dynamically loads and mounts the `reportes` and `prod_peru` FastAPI apps, exposing their static assets and routes. |
| **Health check** | Simple endpoint (`/health`) for monitoring the service status. |

## Repository Structure (relevant parts)

```
R-App1/
├─ FlexStart/
│  ├─ backend/
│  │  └─ app.py          # <-- FastAPI gateway (this file)
│  ├─ assets/            # static assets (CSS, JS, images)
│  ├─ herramientas/      # HTML front‑ends for each tool
│  ├─ data/              # JSON data files (e.g., birthdays.json)
│  ├─ index.html         # main UI entry point
│  └─ ...
└─ README.md             # <-- this document
```

## How to Publish to GitHub

1. **Initialize a Git repository** (if not already initialized):
   ```bash
   cd "/Users/rjarad/Library/Mobile Documents/com~apple~CloudDocs/Apps/App_SUITE/R-App1"
   git init
   ```
2. **Add a `.gitignore`** (recommended to exclude virtual‑environment files, `__pycache__`, and OS artefacts):
   ```bash
   echo "__pycache__/" >> .gitignore
   echo "*.pyc" >> .gitignore
   echo ".DS_Store" >> .gitignore
   ```
3. **Commit the code**:
   ```bash
   git add .
   git commit -m "Initial commit – SUITE Gateway FastAPI application"
   ```
4. **Create a remote repository on GitHub** (via the GitHub UI) and copy the remote URL, e.g. `git@github.com:username/suite-gateway.git`.
5. **Add the remote and push**:
   ```bash
   git remote add origin git@github.com:username/suite-gateway.git
   git branch -M main
   git push -u origin main
   ```

Once pushed, the repository will contain the source code and this `README.md` which provides a clear, representative description of the application’s functionality.
