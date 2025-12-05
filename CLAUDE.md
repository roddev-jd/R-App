# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**App_SUITE v2.0.3** (also branded as "Ripley Apps" or "P&C Suite") is a comprehensive desktop/web hybrid application suite designed for Ripley Corporation's product management, design, and reporting workflows. The system integrates multiple specialized tools for inventory management, product design, workflow automation, and business intelligence reporting.

**Technology**: Python-based polyglot system with FastAPI backend, HTML5/Bootstrap frontend, and multiple desktop applications
**Version**: 2.0.3
**Status**: Production system with active maintenance and updates

---

## Application Type & Architecture

### Hybrid Architecture
- **Desktop Launcher**: tkinter-based GUI launcher application (lanzador.py) for managing and launching the suite
- **Web-based Frontend**: HTML5 + Bootstrap responsive web interfaces served via FastAPI
- **Python Desktop Apps**: Individual GUI tools built with tkinter, PyQt6, or PySide6
- **RESTful Backend**: FastAPI central gateway managing all services and script execution

### Execution Model
The application follows a **modular launcher pattern**:
1. User runs `lanzador.py` - Desktop GUI launcher
2. Launcher starts FastAPI web server on dynamic ports (8005-8050)
3. Browser opens to localhost with web interface
4. Web interface provides navigation to sub-applications and tools
5. Individual tools can be executed as separate processes or served via web

---

## Main Technology Stack

### Backend Framework
- **FastAPI** (v0.104.0+) - Modern async web framework
- **Uvicorn** (v0.24.0+) - ASGI server
- **Pydantic** (v2.4.0+) - Data validation and modeling

### Frontend Framework
- **HTML5 / Bootstrap** (v5.x) - Responsive UI framework
- **Custom CSS/SCSS** - Theme styling
- **Bootstrap Icons** - Icon library
- **Responsive design** - Mobile, tablet, desktop support

### Desktop Applications
- **tkinter** - Standard Python GUI toolkit
- **customtkinter** (v5.2.0+) - Modern tkinter wrapper
- **PyQt6** (v6.4.0+) - Alternative desktop framework
- **PySide6** (v6.4.0+) - Qt bindings alternative

### Data Processing & Database
- **DuckDB** (v0.9.0+) - Columnar database for fast queries and reporting
- **Pandas** (v2.2.0+) - Data manipulation and analysis
- **openpyxl** / **xlsxwriter** - Excel file handling
- **PyArrow** (v14.0.0+) - Data serialization and storage

### Image Processing
- **Pillow** (v10.0.1+) - Image manipulation
- **OpenCV** (optional) - Computer vision capabilities
- **NumPy** (v1.24.3+) - Numerical computing

### Cloud & Storage
- **Azure Storage Blob** (v12.19.0+) - Cloud file storage
- **boto3** (v1.34.0+) - AWS S3 support
- **MSAL** (v1.24.0+) - Azure authentication
- **Sharepoint integration** - Direct document retrieval

### Web Scraping & HTTP
- **requests** (v2.31.0+) - HTTP client
- **beautifulsoup4** (v4.12.0+) - HTML parsing
- **urllib3** (v2.0.0+) - HTTP client utilities

### System & Utilities
- **keyring** (v24.0.0+) - Secure credential storage
- **watchdog** (v3.0.0+) - File system monitoring
- **packaging** (v23.0+) - Version parsing
- **pytest** (v7.4.0+) - Testing framework

---

## Project Structure

**Note**: This repository is `R-App1`, the main application codebase. The launcher (`lanzador.py`) and updater (`updater_v2.py`) may be located in a separate deployment directory.

```
R-App1/
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── CLAUDE.md                  # This file
├── requirements_server.txt    # Server-side Python dependencies
│
└── FlexStart/                 # Main application directory
    ├── __init__.py
    ├── index.html             # Main web portal dashboard
    ├── birthdays.html         # Birthday/calendar module
    ├── metricas.html          # Metrics dashboard
    │
    ├── backend/               # Central backend gateway
    │   ├── app.py            # FastAPI main application (gateway)
    │   ├── __init__.py
    │   ├── FlexStart/        # Backend app integrations
    │   │   └── apps/         # Backend app handlers
    │   │       └── prod_peru/
    │   ├── apps/             # Backend services directory
    │   │   └── prod_peru/    # Production Peru service
    │   └── metricas_services/
    │       ├── metricas_service.py
    │       └── __init__.py
    │
    ├── apps/                  # Individual applications (multimodular)
    │   ├── __init__.py
    │   │
    │   ├── diseno/           # Design Management App (40+ tools)
    │   │   ├── Buscador.py
    │   │   ├── Miniaturas.py
    │   │   ├── CLdownloader.py
    │   │   ├── PEdownloader.py
    │   │   ├── RipleyDownloader.py
    │   │   ├── Scrapper.py
    │   │   ├── Renamer-*.py  # Multiple renaming tools
    │   │   ├── Insert.py
    │   │   ├── Dept.py       # Department organizer
    │   │   ├── Encarpetar.py # Folder grouping
    │   │   ├── Indexar.py / index/
    │   │   ├── Prod-Selector.py
    │   │   ├── TeamSearch.py
    │   │   ├── Compresor.py / Compress/
    │   │   ├── Convertidor.py
    │   │   ├── RotateImg.py
    │   │   ├── MultiTag/     # Multi-tag editor
    │   │   ├── Validador_tamano.py
    │   │   ├── APP_CARGAS_CHILE/
    │   │   ├── APP_CARGAS_PERU/
    │   │   ├── .claude/      # Claude-specific docs
    │   │   └── docs/
    │   │
    │   ├── reportes/         # Reporting Application (Data Analytics)
    │   │   ├── frontend/     # Web UI for reports
    │   │   └── backend/
    │   │       ├── app.py           # FastAPI reportes app
    │   │       ├── main_logic.py    # Core reporting logic
    │   │       ├── config.ini       # Database/data source configs
    │   │       ├── config/          # Config modules
    │   │       ├── core/            # Core utilities
    │   │       │   ├── utils.py
    │   │       │   ├── error_handlers.py
    │   │       │   └── sse_channel.py
    │   │       ├── endpoints/       # API endpoints
    │   │       │   └── sharepoint.py
    │   │       ├── services/        # Business logic services
    │   │       │   ├── data_service.py
    │   │       │   ├── filter_service.py
    │   │       │   ├── export_service.py
    │   │       │   ├── sharepoint_service.py
    │   │       │   └── csv_utils.py
    │   │       └── tests/           # Test suite
    │   │
    │   └── prod_peru/         # Production Peru Declarator
    │       ├── frontend/
    │       └── backend/
    │
    ├── herramientas/          # Tools & Utilities Directory
    │   ├── tools_config.json  # Configuration for 20+ tools
    │   ├── README.md          # Tools documentation
    │   ├── generate_tool_pages.py
    │   ├── update_video.py    # Video management system
    │   ├── test_pages.py
    │   └── [tool].html        # Auto-generated tool pages
    │
    ├── shared/                # Shared modules
    │   ├── __init__.py
    │   ├── capabilities.py    # System capabilities detection
    │   ├── config/            # Shared configurations
    │   ├── themes/            # Theme definitions
    │   └── utils/             # Utility functions
    │
    ├── backend/               # (Alternative backend location)
    │   └── metricas_services/
    │
    ├── frontend/              # Global frontend assets
    │
    ├── assets/                # Static assets
    │   ├── css/
    │   ├── js/
    │   ├── img/
    │   ├── fonts/
    │   ├── vendor/            # Third-party libraries
    │   ├── scss/
    │   └── manuales/          # User manuals
    │
    ├── data/                  # Data files
    │   ├── birthdays.json
    │   └── BIRTHDAYS_README.md
    │
    ├── requirements/          # Python dependencies
    │   ├── requirements_apps.txt
    │   └── requirements-legacy.txt
    │
    ├── update_services/       # Update management
    │
    └── manuales/              # Documentation & manuals
```

---

## Applications & Modules

### 1. **Reportes** (Reporting & Analytics Application)
**Purpose**: Advanced business intelligence and data reporting system
**Type**: Full-stack web application

**Frontend**: Interactive dashboard for data filtering, analysis, and export
**Backend**: 
- `app.py` - FastAPI router and endpoint definitions
- `main_logic.py` - Core data processing and filtering logic (139KB+)
- `config.ini` - Data source configurations (Azure Blob, SharePoint, CSV)
- Services layer:
  - `data_service.py` - Data loading and management
  - `filter_service.py` - Advanced filtering logic
  - `export_service.py` - Data export functionality
  - `sharepoint_service.py` - SharePoint integration
  - `csv_utils.py` - CSV handling utilities

**Key Features**:
- Multi-source data integration (Azure Blob, SharePoint, FTP, CSV)
- Advanced filtering by SKU, tickets, departments, lineamientos
- Dynamic column selection and display
- Real-time data progression with SSE (Server-Sent Events)
- Data export capabilities
- Priority-based color coding
- Pagination support (configurable page sizes)
- DuckDB integration for fast queries

**Data Sources**:
- Chile WOP (Universo SKU) - Azure
- Chile Mejoras (Improvement tracking) - Azure
- Chile Estudios (Photo studies) - Azure
- Peru Staff (Universo SKU) - SharePoint
- Peru Equivalencias (CL->PE mapping) - SharePoint
- Peru Marca Propia (Private labels) - SharePoint

---

### 2. **Diseno** (Design Management App)
**Purpose**: Comprehensive image and product asset management
**Type**: Collection of 40+ Python desktop applications + web interface

**Core Tools** (executed via FastAPI):
- **Buscador.py** - Folder search and copy automation
- **Miniaturas.py** - Thumbnail generation
- **CLdownloader.py** - Chile image downloader
- **PEdownloader.py** - Peru image downloader
- **RipleyDownloader.py** - Universal Ripley image downloader
- **Scrapper.py** - Web scraping for images
- **Insert.py** - Image insertion/cataloging
- **Renamer-*.py** (Multiple variants) - Batch file renaming:
  - Renamer-PH.py (Product House)
  - Renamer-Rimage.py (Rimage system)
  - Renamer-ImgFile.py (File-based)
  - Renamer-Muestras.py (Samples)
- **Indexar.py / index/** - Product indexing system
- **Dept.py** - Department-based file organization
- **Encarpetar.py** - Folder grouping tool
- **Prod-Selector.py** - Product selection interface
- **TeamSearch.py** - Team collaboration search
- **Compresor.py** - Image compression
- **Convertidor.py** - Image format conversion
- **RotateImg.py** - Batch image rotation
- **SVC-OK.py** - Service validation
- **lastImage.py** - Latest image tracking
- **MultiTag/** - Multi-tag editor for bulk tagging
- **image_validator.py** - Size/format validation

**Note**: APP_CARGAS_CHILE and APP_CARGAS_PERU applications may be in separate repositories or deployment packages. They are not present in this R-App1 codebase but are referenced in the larger SUITE ecosystem.

**Frontend**: Tool pages served via herramientas system with:
- Descriptions and features for each tool
- YouTube video embeds (placeholder system)
- One-click execution buttons
- Tool metadata in JSON configuration

---

### 3. **Prod Peru** (Production Peru Declarator)
**Purpose**: Product declaration and compliance system for Peru operations
**Type**: Specialized production tool

**Components**:
- Frontend: Declaration forms and interfaces
- Backend: 
  - `config.ini` - Peru-specific configurations
  - Validation and submission logic

---

## Backend/Frontend Architecture

### Backend Gateway (Central)
**File**: `/FlexStart/backend/app.py`

The central FastAPI gateway serves as the single entry point for all applications:

```
┌─────────────────────────────────────┐
│         Web Browser / UI            │
├─────────────────────────────────────┤
│        index.html (Bootstrap)       │
├─────────────────────────────────────┤
│    FastAPI Central Gateway          │
│    (app.py on port 8005-8050)       │
├─────────────────────────────────────┤
│  ┌─────────────────────────────────┐│
│  │ Route: /reportes/   → Reportes  ││
│  │ Route: /prod_peru   → Prod Peru ││
│  │ Route: /api/scripts → Tool      ││
│  │ Route: /herramientas → Tools    ││
│  │ Route: /assets_*    → Static    ││
│  └─────────────────────────────────┘│
├─────────────────────────────────────┤
│      Sub-Applications/Services      │
│  - Reportes FastAPI                 │
│  - Prod Peru Backend                │
│  - MetricasService                  │
├─────────────────────────────────────┤
│     Python Script Execution         │
│  (ThreadPoolExecutor for 4 workers) │
├─────────────────────────────────────┤
│    External Services                │
│  - Azure Blob Storage               │
│  - SharePoint                       │
│  - FTP (ftp.rjresolve.cl)          │
│  - YouTube (for videos)             │
└─────────────────────────────────────┘
```

**Key Features**:
- Dynamic port allocation (MIN_PORT=8005, MAX_PORT=8050)
- Port persistence via config.ini (LauncherSettings.last_used_port)
- Thread pool execution for long-running scripts
- CORS headers for cross-origin requests
- Static file serving for assets
- Error handling and logging infrastructure
- Server-Sent Events (SSE) for real-time progress
- Request/response validation with Pydantic

**Allowed Scripts Registry** (100+ scripts):
All design tools are registered in `get_allowed_scripts()` with full paths

---

### Frontend Architecture
**Main Portal**: `/FlexStart/index.html`

**Structure**:
- **Header**: Logo (Ripley Apps), navigation menu
- **Hero Section**: Welcome message and featured tools
- **Navigation Sections**:
  - Home/Inicio
  - Reportes (button) → `/reportes/`
  - Declarador (button) → `/prod_peru`
  - Happy Birthday (button) → `/birthdays.html`
  - Diseno section
  - Redaccion section
  - Manuales (documentation)

**Asset Organization**:
- CSS: Bootstrap + custom styles
- JS: Bootstrap and app-specific scripts
- Images: Icons, logos, product images
- Fonts: Roboto, Poppins, Nunito
- Vendor: Third-party libraries (Bootstrap, AOS, Glightbox, Swiper)
- Manuales: User guides and help documentation

---

## Launcher System

### Desktop Launcher (`lanzador.py`)
**Type**: tkinter GUI application

**Responsibilities**:
1. System dependency checking
2. Python environment validation
3. Virtual environment management
4. FastAPI server startup
5. Port allocation and management
6. Configuration file handling
7. Update checking and execution
8. Browser auto-launch
9. Process monitoring
10. Error reporting and recovery

**Key Features**:
- Custom toggle switch widgets
- Configuration persistence (ConfigParser)
- Port cycling (8005-8050 range)
- Integration with updater_v2.py
- Graceful server shutdown
- Automatic cleanup

---

## Configuration System

### Primary Config Files

**1. `/FlexStart/apps/reportes/backend/config.ini`** (Main)
Sections:
- `[FTP]` - FTP server credentials
- `[Azure]` - Azure Blob Storage connection
- `[Blobs]` - Data source definitions (20+ sources)
- `[LauncherSettings]` - Launcher configuration (port, etc.)

Example blob sources:
- Chile_Wop - Complete SKU universe (Chile)
- Chile_MejorasCL - Improvement tracking
- Peru_Staff - Staff/SKU data (SharePoint)
- Peru_eqs - Chile-Peru equivalencies
- Peru_Data_Script - Private label data

**2. `/FlexStart/herramientas/tools_config.json`** (Tools Metadata)
Defines 20+ tools with:
- Name, subtitle, category, type
- Icons and execution script IDs
- Long descriptions (HTML)
- Features list
- Video URLs
- Metadata for tool pages

**3. `/FlexStart/apps/prod_peru/backend/config.ini`** (Peru-specific)
Peru operation configurations

---

## Data Flow

### Typical Report Generation Flow

```
Browser User Interface
    ↓
index.html → Select filters/columns
    ↓
FastAPI Gateway (/reportes)
    ↓
Reportes Backend (app.py)
    ↓
FilterRequest Validation (Pydantic)
    ↓
Filter Service
    ↓
Data Service (loads from config sources)
    ↓
Azure/SharePoint/CSV Data Retrieval
    ↓
DuckDB Query Execution (fast SQL)
    ↓
Export Service (CSV/Excel/JSON)
    ↓
SSE Progress Updates → Browser
    ↓
JSON Response → Display in UI
```

### Script Execution Flow

```
Web Interface (Tool Button Click)
    ↓
POST /api/scripts/{script_id}
    ↓
Validate script_id in ALLOWED_SCRIPTS
    ↓
ThreadPoolExecutor.submit(_execute_script_sync)
    ↓
subprocess.Popen (separate process)
    ↓
PYTHONPATH setup for local imports
    ↓
Script execution in own window (GUI) or headless
    ↓
JSON Response (PID, status)
    ↓
Browser receives success/error feedback
```

---

## Update System

### Version Management (`updater_v2.py`)
**Version URL**: `https://www.rjresolve.cl/descargas/version.json`

**Responsibilities**:
- Version checking
- Complete file downloads
- Dependency installation
- Rollback capability
- Progress reporting

**Update Process**:
1. Check remote version
2. Download complete zip if newer
3. Backup existing files
4. Extract new files
5. Install Python requirements
6. Validate installation
7. Cleanup old files

---

## Dependencies & Requirements

### Core Dependencies (requirements_apps.txt)

**Web Framework** (1):
- fastapi, uvicorn, pydantic, starlette, python-multipart

**Database** (2):
- duckdb, pyarrow

**GUI** (3):
- customtkinter, ttkbootstrap, tkinter-tooltip, PyQt6, PySide6

**Image Processing** (4):
- Pillow, numpy

**Data Processing** (5):
- pandas, openpyxl, xlsxwriter

**Cloud** (6):
- azure-storage-blob, boto3, msal

**HTTP** (7):
- requests, urllib3, beautifulsoup4

**System** (8):
- packaging, keyring, watchdog, cachetools

**Testing** (9):
- pytest

**Total**: 50+ package dependencies

---

## Special Features & Capabilities

### 1. **Capabilities System** (`/shared/capabilities.py`)
Detects and reports system capabilities:
- DuckDB availability
- OpenCV availability
- Reportes module
- AHEAD facial recognition tool

### 2. **Metrics Service**
`/backend/metricas_services/metricas_service.py`
- System monitoring
- Performance tracking
- Usage analytics

### 3. **SSE (Server-Sent Events)**
Real-time progress streaming:
- `search_progress_queue` - Search operation progress
- `data_load_progress_queue` - Data loading progress
- Allows browser to receive live updates without polling

### 4. **Tool Pages Generator** (`/herramientas/generate_tool_pages.py`)
Auto-generates HTML pages for tools:
- Templates from tools_config.json
- Video embed support
- Consistent styling
- Dynamic page generation

### 5. **Birthday System** (`birthdays.html`)
Separate module for birthday/calendar management

### 6. **Metrics Dashboard** (`metricas.html`)
Aggregated system metrics and KPIs

---

## File Organization Patterns

### Apps Structure (Modular)
Each app typically follows:
```
app_name/
├── .git/                    # Git repository
├── .gitignore
├── .last_port              # Last used port
├── README.md               # App documentation
├── backend/
│   ├── app.py             # FastAPI app
│   ├── config.ini         # Configuration
│   ├── main_logic.py      # Core logic
│   ├── services/          # Business logic
│   ├── endpoints/         # API routes
│   ├── core/              # Core utilities
│   ├── config/            # Config modules
│   └── tests/             # Tests
└── frontend/
    ├── index.html
    ├── static/
    └── assets/
```

### Shared Code Organization
```
shared/
├── capabilities.py         # System detection
├── config/                # Config utilities
├── themes/                # Theme definitions
└── utils/                 # General utilities
```

---

## Common Development Commands

### Running the Application
```bash
# Start the central FastAPI gateway (main backend)
cd FlexStart/backend
uvicorn app:app --reload --port 8005

# Or run from any directory (using full path)
python -m uvicorn FlexStart.backend.app:app --reload --port 8005

# Run specific app backend directly (for development)
cd FlexStart/apps/reportes/backend
uvicorn app:app --reload --port 8010

# Run individual design tools (standalone)
cd FlexStart/apps/diseno/BUSCADOR
python Buscador.py

cd FlexStart/apps/diseno/MINIATURAS
python Miniaturas.py
```

### Testing Commands
```bash
# Run reportes backend tests
cd FlexStart/apps/reportes/backend/tests
pytest test_database_loading.py
python test_runner.py
python run_diagnosis.py

# Test individual design tools
cd FlexStart/apps/diseno/BUSCADOR
python Buscador.py

cd FlexStart/apps/diseno/MINIATURAS
python Miniaturas.py

# Test specific INDEXAR tool
cd FlexStart/apps/diseno/INDEXAR
python test_app.py
```

### Tool Management
```bash
# Regenerate all tool pages from tools_config.json
cd FlexStart/herramientas
python3 generate_tool_pages.py

# Add YouTube video to a tool
python3 update_video.py buscador_diseno "https://youtube.com/watch?v=VIDEO_ID"

# Test generated tool pages
python3 test_pages.py

# Available tool IDs (from tools_config.json):
# buscador_diseno, miniaturas_diseno, CLdownloader, PEdownloader,
# RipleyDownloader, Scrapper, Renamer-PH, Renamer-Rimage, SVC-OK,
# Renamer-ImgFile, Renamer-Muestras, lastImage, Insert, Dept,
# Encarpetar, Indexar, Prod-Selector, TeamSearch, Compresor,
# Convertidor, RotateImg, Multi-Tags-moda-producto, Validador_tamano
```

### Dependencies Installation
```bash
# Install server-side dependencies (minimal set for FastAPI gateway)
pip install -r requirements_server.txt

# Install dependencies for specific apps
pip install -r FlexStart/apps/diseno/INDEXAR/requirements.txt
pip install -r FlexStart/apps/diseno/MULTITAG/requirements.txt

# Note: Full dependency list is in the comprehensive SUITEV2.0.2 distribution
# This repository contains the core application code
```

### Production Deployment
- FastAPI backend runs on dynamic ports (8005-8050)
- Port configuration stored in config.ini files
- Static files served via FastAPI StaticFiles middleware
- Scripts executed via ThreadPoolExecutor (4 workers max)
- Auto-update capability managed by external updater system

---

## Security Considerations

### Credentials Management
- `config.ini` stores FTP/Azure credentials
- Not committed to git (.gitignore)
- Uses keyring library for secure storage (optional)

### Script Execution
- Whitelist-based script execution (ALLOWED_SCRIPTS)
- Scripts run in subprocess (isolated)
- ThreadPoolExecutor with limited workers (4)

### API Validation
- Pydantic models validate all requests
- Type checking on all inputs
- Error handling middleware

---

## Performance Optimizations

1. **DuckDB**: Columnar database for 10-100x faster queries
2. **Async FastAPI**: Non-blocking I/O
3. **ThreadPoolExecutor**: Multi-threaded script execution
4. **SSE Events**: Real-time progress without polling
5. **Static file caching**: Browser caching of assets
6. **Lazy loading**: On-demand data retrieval

---

## Documentation Sources

- `/CLAUDE.md` - This file (project overview and architecture)
- `/FlexStart/herramientas/README.md` - Tools system documentation
- `/FlexStart/apps/diseno/INDEXAR/README.md` - INDEXAR tool documentation
- Various app-specific `.claude/` directories for detailed app documentation
- Tool videos via YouTube (configurable in tools_config.json)

---

## Key Development Patterns

### Port Management
```python
MIN_PORT = 8005
MAX_PORT = 8050
# Cycles through available ports, persists in config.ini
```

### Configuration Inheritance
```
lanzador.py → Flask/reportes/backend/config.ini → All sub-apps
```

### Service Layer Pattern
All apps use service-based architecture:
- Service instantiation with dependencies
- Interface segregation
- Testable with mocking

### Error Handling
- Custom error handlers in endpoints
- Structured logging (timestamps, levels, module names)
- User-friendly error messages

---

## Version History

- **v2.0.2**: Current (November 2025)
- **v2.0.x**: Multi-app integrated suite
- **v1.4.7**: Previous stable release
- **v1.4.3**: Legacy requirements set

---

## Future Architecture Considerations

1. **Microservices**: Individual apps could be deployed independently
2. **Database**: Migration to centralized PostgreSQL for shared data
3. **WebSocket**: Real-time bidirectional communication
4. **Docker**: Containerization for deployment
5. **API Gateway**: Dedicated reverse proxy (nginx)
6. **Authentication**: User management and role-based access
7. **Monitoring**: Prometheus/Grafana integration
8. **CDN**: Static asset delivery optimization

---

## Important Implementation Notes

### Directory Structure Pattern
Design tools follow uppercase directory naming:
- `FlexStart/apps/diseno/BUSCADOR/` contains `Buscador.py`
- `FlexStart/apps/diseno/MINIATURAS/` contains `Miniaturas.py`
- Directory names use UPPERCASE, script names use PascalCase

### Script Execution via Gateway
The central gateway (`FlexStart/backend/app.py`) manages all script execution:
- Scripts registered in `ALLOWED_SCRIPTS` dictionary
- Executed via `ThreadPoolExecutor` with 4 workers
- Run in separate processes using `subprocess.Popen`
- PYTHONPATH configured for local imports
- Returns PID and status as JSON response

### Configuration Files
- `.env.example` - Template for environment variables (Azure credentials, etc.)
- `config.ini` files scattered across apps (reportes, prod_peru)
- `tools_config.json` - Master configuration for all design tools

### Missing from This Repository
This codebase (R-App1) contains the core application logic but may not include:
- Desktop launcher (`lanzador.py`) - likely in separate deployment package
- Auto-updater (`updater_v2.py`) - likely in separate deployment package
- Complete requirements files - see `requirements_server.txt` for minimal set
- APP_CARGAS applications - may be in separate repositories

---

**Last Updated**: December 5, 2025
**Architecture Version**: 2.0.3
**Repository**: R-App1 (Core Application Codebase)
**Maintainer**: Ripley Product & Category Team
