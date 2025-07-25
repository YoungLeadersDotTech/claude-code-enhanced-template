# Context Exporter

A generic tool for exporting content from Confluence and Jira based on specified labels.

## Overview

The `context_exporter.py` script has been refactored from the original `easy_pay_export.py` to be a generic, reusable tool that can export content from both Confluence and Jira based on any specified label.

## Key Changes

### 1. **Generic Naming**
- Renamed from `easy_pay_export.py` to `context_exporter.py`
- Class renamed from `EasyPayExporter` to `ContextExporter`
- Output directory changed from `easy_pay_exports` to `context_exports`

### 2. **Dynamic Label Support**
- Removed all hardcoded "EasyPayExport" references
- Added `label` parameter to the constructor
- All search queries now use the dynamic label parameter
- Command-line argument support for specifying labels

### 3. **Updated Messages**
- All log messages and output now say "Context Export" instead of "Easy Pay Export"
- PDF filenames include the label in the format: `ContextExport_{label}_{type}_{name}_{date}.pdf`

## Usage

### Basic Usage
```bash
# Export content with default label (EasyPayExport)
python3 context_exporter.py

# Export content with specific label
python3 context_exporter.py "MyCustomLabel"

# Export content with different label
python3 context_exporter.py "QA_Review"
```

### Examples
```bash
# Export EasyPayExport content (same as before)
python3 context_exporter.py EasyPayExport

# Export content with different label
python3 context_exporter.py "Release_Notes"

# Export content with another label
python3 context_exporter.py "Documentation"
```

## Features

- **Confluence Export**: Searches for pages with the specified label and exports them as PDFs
- **Jira Export**: Searches for issues with the specified label and exports them as PDFs
- **Recursive Content**: Includes child pages and smart links up to 4 levels deep
- **Comprehensive Fields**: Exports all available Jira fields in organized sections
- **PDF Generation**: Creates well-formatted PDFs with table of contents and proper styling

## Output

The script generates PDF files in the `context_exports` directory with the naming convention:
- `ContextExport_{label}_Confluence_{space_name}_{date}.pdf`
- `ContextExport_{label}_Jira_{project_name}_{date}.pdf`

## Configuration

The script uses environment variables for configuration:
- `CONFLUENCE_URL`: Your Confluence instance URL
- `JIRA_URL`: Your Jira instance URL  
- `ATLASSIAN_USERNAME`: Your Atlassian username
- `ATLASSIAN_API_TOKEN`: Your Atlassian API token

## Migration from easy_pay_export.py

If you were using the original script, simply replace:
```bash
python3 easy_pay_export.py
```

With:
```bash
python3 context_exporter.py EasyPayExport
```

The functionality remains exactly the same, but now you can use any label you want! 