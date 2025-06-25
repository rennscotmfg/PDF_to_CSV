# Calypso PDF to CSV/JSON Converter - Installation Guide

A web-based tool for converting Calypso CMM (Coordinate Measuring Machine) PDF reports into structured CSV or JSON format for data analysis.

⚠️ Notice: This code is provided for review and reference only. It is not open source and may not be used, copied, or modified without explicit permission.

## Features

- **Multi-file Processing**: Upload and process multiple PDF files simultaneously
- **Intelligent Data Extraction**: Extracts dimensional measurements (DIM values) with proper sorting
- **Transposed Output**: Creates CSV with dimensions as rows and parts as columns
- **Statistical Analysis**: Optional statistics (mean, min, max, standard deviation)
- **Modern Web Interface**: Drag-and-drop file upload with real-time preview

## Prerequisites

- **Python 3.7 or higher**
- **pip** (Python package installer)
- **Web browser** (Chrome, Firefox, Safari, Edge)

## Installation

### 1. Download or Clone the Project

```bash
# If using git
git clone <repository-url>
cd PDF_to_CSV

# Or download and extract the ZIP file
```

### 2. Set Up Python Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Required Packages

```bash
# Install all dependencies
pip install -r requirements.txt
```

**Manual installation (if requirements.txt fails):**
```bash
pip install Flask==2.3.3
pip install pdfplumber==0.9.0
pip install pandas==2.0.3
pip install Werkzeug==2.3.7
```

## Running the Application

### 1. Start the Flask Server

```bash
# Make sure virtual environment is activated
python app.py
```

You should see output similar to:
```
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://[your-ip]:5000
```

### 2. Access the Web Interface

Open your web browser and navigate to:
- **Local access**: http://localhost:5000
- **Network access**: http://[your-computer-ip]:5000

### 3. Using the Application

1. **Upload PDFs**: Drag and drop or click to select Calypso PDF files
2. **Process Files**: Click "Process Files" to extract measurement data
3. **Preview Data**: Review the extracted measurements in the preview table
4. **Download CSV**: Choose options and download your structured data

## Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Try a different port
python -c "from app import app; app.run(port=5001)"
```

**Permission errors on Windows:**
```bash
# Run as administrator or check antivirus settings
```

**PDF processing errors:**
```bash
# Ensure PDFs are not password-protected
# Check that PDFs contain text (not just images)
```

**Module not found errors:**
```bash
# Reinstall dependencies
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

### Debug Mode

For detailed error messages, run with debug enabled:
```bash
# app.py already has debug=True set
python app.py
```

## File Structure

The application creates the following structure:
```
uploads/                 # Temporary PDF storage (auto-created)
├── temp_file1.pdf      # Automatically cleaned up
└── temp_file2.pdf      # Automatically cleaned up
```

## System Requirements

- **RAM**: 4GB minimum (8GB recommended for large PDFs)
- **Storage**: 100MB free space
- **Network**: Local network access for multi-user scenarios

## Security Notes

- The application runs on `0.0.0.0` (all interfaces) for network access
- Files are temporarily stored and automatically deleted
- Maximum upload size is 16MB per file
- Only PDF files are accepted

## Stopping the Application

Press `Ctrl+C` in the terminal to stop the Flask server.

To deactivate the virtual environment:
```bash
deactivate
```

## Next Steps

- Place your Calypso PDF reports in an accessible folder
- Test with a small batch of PDFs first
- Review the CSV output format to ensure it meets your analysis needs
- Consider setting up the application on a dedicated server for team use

## Support

If you encounter issues:
1. Check that all dependencies are installed correctly
2. Verify your PDF files are not corrupted
3. Review the console output for detailed error messages
4. Ensure sufficient disk space and memory

---

**Version**: 2.0 
**Tested with**: Python 3.8+, Flask 2.3.3  
**Supported PDFs**: Calypso CMM measurement reports