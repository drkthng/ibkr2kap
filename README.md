# IBKR2KAP

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.12%2B-blue" alt="Python Version">
  <img src="https://img.shields.io/badge/Status-v1.0%20Core%20Complete-success" alt="Status">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
</div>

<br>

**IBKR2KAP** is a robust, local-first application designed specifically for German retail investors and traders who use Interactive Brokers (IBKR). It bridges the gap between IBKR's complex reporting and the strict requirements of German tax law, automating the generation of data ready for the **Anlage KAP** (Einkommensteuererklärung).

## 🚀 Key Features

*   **Accurate Data Ingestion:** Parses IBKR Flex Query XML files (and provides a fallback for CSV Activity Statements).
*   **Strict Financial Precision:** Uses Python's `decimal` type and SQLAlchemy 2.0 (with SQLite) to ensure absolute precision. Floating-point errors are unacceptable in tax reporting.
*   **Tax-Compliant FIFO Engine:** Accurately matches buys and sells according to the First-In, First-Out (FIFO) principle required by German tax law, using settlement dates (Settle-Date).
*   **German Tax Categorization:** Automatically separates gains and losses into the correct German tax pools:
    *   *Aktienverrechnungstopf* (Losses from stocks can only be offset against stock gains).
    *   *Termingeschäfte* (Options and Futures).
    *   *Sonstige* (Dividends, Interest, etc.).
*   **§ 23 EStG Compliance (Currency Gains):** Features a dedicated FX FIFO engine to track pools of foreign currency (e.g., USD) and automatically identifies taxable exchange rate gains/losses for currency held for 1 year or less.
*   **Complex Options Handling:** Correctly handles option edge cases, including expirations, assignments, and exercises (e.g., adjusting the underlying stock's cost basis using the option premium).
*   **Corporate Actions:** Seamlessly interleaves stock splits and other corporate actions into the FIFO matching timeline.
*   **ECB Official Rates:** Fetches and caches official European Central Bank (ECB) exchange rates, including logic to correctly handle weekends and holidays per BMF guidelines.
*   **Tax Consultant Ready:** Generates an elegantly formatted `.xlsx` Excel report that directly maps to the lines of the **Anlage KAP** (Lines 7, 8, 9, 10, 15).
*   **Local & Secure:** A Streamlit-based UI runs entirely on your local machine. No data is sent to the cloud.

## 🛠️ Technology Stack

*   **Backend:** Python 3.12+, `pydantic` v2 (for strict data validation), `ibflex` (for reliable XML parsing).
*   **Database:** SQLite via `SQLAlchemy 2.0` ORM.
*   **Frontend:** `Streamlit` for a fast, responsive local web interface.
*   **Testing:** `pytest` with near 100% coverage on core logic.
*   **Package Management:** `uv` (or `poetry`).

## 📥 Installation

Because IBKR2KAP processes sensitive financial data, it is designed to be run locally from source.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/IBKR2KAP.git
    cd IBKR2KAP
    ```

2.  **Set up the environment (using `uv`):**
    ```bash
    uv venv
    uv pip install -e .
    ```
    *(Alternatively, you can use `pip install -r requirements.txt` or `poetry install` if configured).*

3.  **Run migrations / Initialize DB:**
    ```bash
    # (Documentation to be added for Alembic or auto-init script)
    ```

4.  **Start the UI:**
    ```bash
    streamlit run src/ibkr_tax/main.py
    ```

## 📊 Usage

1.  **Export from IBKR:** 
    *   Log into IBKR Client Portal.
    *   Go to Reports / Tax Docs -> Flex Queries.
    *   Create a new **Activity Flex Query** encompassing the tax year you need.
    *   Ensure all sections are included (Trades, Cash Transactions, Corporate Actions, Open Positions).
    *   Export as **XML**.
2.  **Import to IBKR2KAP:** Open the Streamlit app in your browser, upload the XML file.
3.  **Process:** Click "Run Tax Engine". The system will ingest the data, run the FIFO matching (both Asset and FX), and categorize the output.
4.  **Export:** Download the generated Excel (`.xlsx`) report and hand it to your *Steuerberater* (Tax Consultant).

## ⚠️ Disclaimer

**This software does not constitute tax advice.** 
IBKR2KAP is a tool designed to assist in calculating and preparing data. German tax law is highly complex and subject to change. You are solely responsible for the accuracy of your tax declaration. Always verify the output and consult a certified tax advisor (*Steuerberater*) before submitting your tax return.

## 🤝 Contributing

Contributions are welcome! If you find a bug (especially an edge case with IBKR's ever-changing export formats) or want to add a feature (e.g., support for Mergers/Spinoffs), please open an issue or submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
