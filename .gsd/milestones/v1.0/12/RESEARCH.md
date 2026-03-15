# Phase 12 Research: Streamlit UI Integration

## Objective
Identify how a new Streamlit frontend (`src/app.py` or similar) will integrate with the existing business logic (Phase 1-11) for the IBKR2KAP application.

## API Integration Points

Based on codebase analysis, the Streamlit app needs to orchestrate the following:

1. **Database Session Initialization**
   - Import `get_session` or `engine` from `ibkr_tax.db.database`.
   - Setup a centralized way to pass a DB session to backend services during Streamlit runs.

2. **Data Import Pipeline (`ibkr_tax.services.pipeline.run_import`)**
   - Streamlit `st.file_uploader` to accept XML or CSV files.
   - Save the uploaded file temporarily to disk, as `run_import(file_path: str, session: Session, file_type: str)` requires a string path.
   - Return counts dictionary to display success metrics to the user.

3. **FIFO Engine (`ibkr_tax.services.fifo_runner.FIFORunner`)**
   - Provide a button to trigger `FIFORunner(session).run_all()` or specific account runs.
   - This prepares the `Gain` and `FIFOLot` tables for the tax year.

4. **Tax Aggregation (`ibkr_tax.services.tax_aggregator.TaxAggregatorService`)**
   - Allow user to provide `account_id` (string identifier from Flex Query) and `tax_year`.
   - Call `TaxAggregatorService(session).generate_report(account_id, tax_year)`.
   - Display `TaxReport` Pydantic model fields (KAP Lines 7, 8, 9, 10, 15) in a clean Streamlit dataframe or metrics view.

5. **Excel Export (`ibkr_tax.services.excel_export.ExcelExportService`)**
   - Use the generated `TaxReport`.
   - Call `ExcelExportService(session).export(report, temp_path)`.
   - Streamlit `st.download_button` pointing to the generated Excel file.

## Streamlit Architecture Recommendation
- **Single Page App with Tabs/Sidebar**: Use `st.tabs(["Import Data", "Run Tax Engine", "Export Reports"])` or a sidebar navigation.
- **State Management**: Minimal state needed, just passing variables or relying on the local SQLite DB as the source of truth.
- **File Handling**: Use `tempfile` module to save uploaded files (XML/CSV) and to generate the Excel report for download.

## Dependencies needed
- `streamlit` (already expected in pyproject.toml / uv configuration, might need to run `uv add streamlit` if not present.)
