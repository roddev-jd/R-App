# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

### Main Application
```bash
python app_cargas.py
```
Launches the GUI application for comparing folder names with Azure Blob Storage data and generating Excel reports.

### Installing Dependencies
```bash
pip install -r requirements.txt
```
Installs all required packages including Azure Blob Storage client, pandas, and openpyxl.

### Testing and Utilities
```bash
# Test folder coincidences with real data
python test_coincidencias.py

# List files in Azure Blob Storage containers
python listar_blobs.py
python listar_vertica.py

# Run individual test files
python test_contenedores.py
python test_materialidad.py
```

### Development Workflow
When modifying the application, test changes using the utility scripts before running the full GUI:
1. Use `test_coincidencias.py` to verify data processing logic with real Azure data
2. Use `listar_blobs.py` and `listar_vertica.py` to explore available data sources
3. Run the main application for full integration testing

## Project Architecture

### Core Application (app_cargas.py)
The main application is a **Tkinter-based GUI** that:
- Allows users to select a folder location containing subfolders
- Downloads CSV data from Azure Blob Storage (`tabla_wop_completa.csv` and optionally `TABLAS_VERTICA/c1_materialidad.csv`)
- Compares folder names with `sku_hijo_largo` column in the CSV
- Generates Excel reports with two sheets:
  - **Coincidencias Relacionadas**: Exact matches plus all records sharing the same `sku_padre_largo` and `color`
  - **Coincidencias Exactas**: Only exact matches between folder names and `sku_hijo_largo`

### Key Components
- **Threading**: Non-blocking UI with `threading.Thread` for processing
- **Real-time Events**: Queue-based event system for UI updates during processing
- **Progress Tracking**: Visual progress bar and detailed logging
- **Azure Integration**: Azure Blob Storage client with credential management
- **Automatic JOIN**: Always enriches data with `COMPROMISO_R` via JOIN between `sku_padre_corto` and `COD_PADRE`
- **Caching System**: Local file caching in `cache/` directory for downloaded CSV files
- **Additional Reports**: Optional MODA/PRODUCTO planillas and departmental responsibility reports
- **Email Templates**: HTML template generation for email notifications with structured data

### Data Flow
1. **Input**: User selects folder location containing subfolders
2. **Download**: Azure Blob CSV files (`datascience` container)
3. **Processing**: 
   - Extract folder names
   - Find exact matches with `sku_hijo_largo`
   - Find related records via `sku_padre_largo` + `color`
   - Automatic enrichment with materialidad data
4. **Output**: Excel file with structured results

### Azure Blob Storage Configuration
- **Primary Container**: `datascience`
- **Primary CSV**: `tabla_wop_completa.csv`
- **Secondary CSV**: `TABLAS_VERTICA/c1_materialidad.csv` (for enrichment)
- **Credential Priority**: keyring → environment variable → hardcoded fallback

### Class Structure
- `AppCargas`: Main application class (app_cargas.py:21-1375)
  - **UI Management**: Tkinter-based interface with threading for non-blocking operations
  - **Event System**: Queue-based communication between processing thread and UI thread
  - **Azure Integration**: Multi-tier credential management (keyring → env var → hardcoded)
  - **Data Processing Pipeline**: Folder scanning → CSV matching → Excel report generation
  - **Caching Layer**: Local file caching in `cache/` directory to avoid repeated downloads
  - **Report Generation**: Multiple output formats (Excel, HTML email templates, departmental reports)
  - **Progress Tracking**: Real-time status updates and detailed logging system

### Key Architectural Patterns
- **Producer-Consumer Pattern**: Main thread produces events, UI thread consumes via queue
- **Template Method Pattern**: Standardized data processing flow with customizable steps
- **Strategy Pattern**: Multiple credential sources and report formats
- **Observer Pattern**: Real-time UI updates during background processing

## Dependencies
All dependencies are managed via `requirements.txt`:
- `azure-storage-blob==12.19.0`: Azure Blob Storage client
- `pandas==2.1.4`: Data manipulation and analysis
- `openpyxl==3.1.2`: Excel file generation
- `tkinter`: GUI framework (built into Python)

## Data Processing Logic
- **Normalization**: Handles string vs int data type mismatches (app_cargas.py:708-714)
- **Deduplication**: Prevents JOIN duplicates in materialidad enrichment (app_cargas.py:832)
- **Case Sensitivity**: Performs exact string matching
- **Null Handling**: Graceful handling of missing `sku_padre_corto` values
- **Diagnostic Mode**: Detailed logging for troubleshooting data mismatches (app_cargas.py:610-698)

## File Structure and Important Directories
- `cache/`: Local storage for downloaded CSV files to avoid repeated downloads
- `docs/`: Contains country-specific Excel files (CHILE.xlsx, PERU.xlsx) for departmental responsibility mapping
- `test_*.py`: Individual test scripts for specific functionality testing
- `listar_*.py`: Utility scripts for exploring Azure Blob Storage contents

## Error Handling and Debugging
- **Diagnostic Mode**: Comprehensive data analysis in `diagnosticar_datos()` method (app_cargas.py:610-698)
- **Thread Safety**: All UI updates go through event queue to prevent race conditions
- **Graceful Degradation**: Application continues with available data even if enrichment fails
- **Connection Resilience**: Multi-tier fallback for Azure credentials and connection handling
- **Cache Management**: Automatic cache validation with user-controlled cleanup options

## Threading Architecture
The application uses a sophisticated threading model to maintain UI responsiveness:
- **Main Thread**: Handles all UI operations and event processing
- **Processing Thread**: Performs all data operations (Azure downloads, processing, Excel generation)
- **Communication**: `queue.Queue` for thread-safe message passing
- **Synchronization**: Progress updates and log messages are queued and processed by main thread

## Data Processing Flow
1. **Input Validation**: Verify folder structure and accessibility
2. **Data Acquisition**: Download/cache CSV files from Azure Blob Storage
3. **Matching Engine**: Compare folder names with `sku_hijo_largo` values
4. **Data Enrichment**: JOIN with materialidad data using `sku_padre_corto` → `COD_PADRE`
5. **Relationship Discovery**: Find related records via `sku_padre_largo` + `color` combinations
6. **Report Generation**: Create Excel workbooks with multiple sheets and formatting
7. **Optional Outputs**: Generate additional reports (MODA/PRODUCTO, departmental, email templates)

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.