# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

### Main Application
```bash
python app_cargas.py
```
Launches the GUI application for comparing folder names with SharePoint Online data and generating Excel reports.

### Installing Dependencies
```bash
pip install -r requirements.txt
```
Installs all required packages including MSAL for SharePoint authentication, requests, pandas, and openpyxl.

### Development Workflow
Test changes by running the main application and using the built-in diagnostic features:
1. Use the application's diagnostic mode for troubleshooting data processing logic
2. Check the `cache/` directory for downloaded data files
3. Review generated Excel reports to verify output format and data accuracy

## Project Architecture

### Core Application (app_cargas.py)
The main application is a **Tkinter-based GUI** that:
- Allows users to select a folder location containing subfolders
- Downloads CSV data from SharePoint Online (`formato_ppias.csv`)
- Compares folder names with `sku_hijo_largo` column (mapped from `EAN_HIJO`) in the CSV
- Generates Excel reports with two sheets:
  - **Coincidencias Relacionadas**: Exact matches plus all records sharing the same `sku_padre_largo` and `color`
  - **Coincidencias Exactas**: Only exact matches between folder names and `sku_hijo_largo`

### Key Components
- **Threading**: Non-blocking UI with `threading.Thread` for processing
- **Real-time Events**: Queue-based event system for UI updates during processing
- **Progress Tracking**: Visual progress bar and detailed logging
- **SharePoint Integration**: MSAL-based OAuth 2.0 authentication with SharePoint Online
- **Column Mapping**: Automatic mapping from SharePoint columns to internal system columns
- **Caching System**: System-wide file caching in `~/.appsuite_cache/data/` directory for downloaded CSV files
- **Additional Reports**: Optional MODA/PRODUCTO planillas and departmental responsibility reports
- **Email Templates**: HTML template generation for email notifications with structured data

### Data Flow
1. **Input**: User selects folder location containing subfolders
2. **Authentication**: OAuth 2.0 authentication with SharePoint using MSAL
3. **Download**: SharePoint CSV file (`formato_ppias.csv`)
4. **Column Mapping**: Map SharePoint columns to internal system columns
5. **Processing**:
   - Extract folder names
   - Find exact matches with `sku_hijo_largo` (mapped from `EAN_HIJO`)
   - Find related records via `sku_padre_largo` + `color`
6. **Output**: Excel file with structured results including new `talla` column

### SharePoint Configuration
- **Site URL**: `https://ripleycorp.sharepoint.com/sites/Equipopyc`
- **CSV File**: `formato_ppias.csv` (Peru - Data Script)
- **Authentication**: MSAL with Azure CLI public client
- **Token Cache**: Local persistent cache in `~/.appsuite_cache/`

### Column Mapping (SharePoint → Internal)
- **EAN_HIJO** → `sku_hijo_largo`
- **EAN_PADRE** → `sku_padre_largo`
- **COLOR** → `color`
- **VARIACION_PMM** → `sku_descripcion`
- **COD DPTO** → `depto`
- **MARCA** → `marca`
- **TALLA** → `talla` (new column)

### Class Structure
- `AppCargas`: Main application class (app_cargas.py:21-1375)
  - **UI Management**: Tkinter-based interface with threading for non-blocking operations
  - **Event System**: Queue-based communication between processing thread and UI thread
  - **SharePoint Integration**: MSAL OAuth 2.0 authentication with persistent token cache
  - **Column Mapping**: Automatic transformation from SharePoint to internal column names
  - **Data Processing Pipeline**: Folder scanning → CSV matching → Excel report generation
  - **Caching Layer**: System-wide file caching in `~/.appsuite_cache/data/` directory to avoid repeated downloads
  - **Report Generation**: Multiple output formats (Excel, HTML email templates, departmental reports)
  - **Progress Tracking**: Real-time status updates and detailed logging system

### Key Architectural Patterns
- **Producer-Consumer Pattern**: Main thread produces events, UI thread consumes via queue
- **Template Method Pattern**: Standardized data processing flow with customizable steps
- **Strategy Pattern**: Multiple credential sources and report formats
- **Observer Pattern**: Real-time UI updates during background processing

## Dependencies
All dependencies are managed via `requirements.txt`:
- `msal==1.24.0`: Microsoft Authentication Library for SharePoint OAuth 2.0
- `requests==2.31.0`: HTTP library for SharePoint API calls
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
- `~/.appsuite_cache/data/`: System-wide cache directory for downloaded CSV files to avoid repeated downloads (keeps project lightweight)
- `docs/`: Contains country-specific Excel files (CHILE.xlsx, PERU.xlsx) for departmental responsibility mapping
- `__pycache__/`: Python bytecode cache directory
- `requirements.txt`: Project dependencies
- `README.md`: Spanish language documentation and usage instructions

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