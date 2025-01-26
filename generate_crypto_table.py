import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
from bs4 import BeautifulSoup

# Environment config
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME')
WORKSHEET_NAME = os.getenv('WORKSHEET_NAME')

def format_values(df):
    """
    Formats numerical columns:
      - Current Price (USD) and ATH Price (USD): 5 decimal places
      - Multiply to Price ATH: 2 decimal places
    """
    def format_price_5dec(x):
        if pd.isnull(x):
            return "N/A"
        try:
            return f"${float(x):,.6f}"
        except:
            return str(x)
    
    # Apply formatting if these columns exist
    if 'Current Price (USD)' in df.columns:
        df['Current Price (USD)'] = df['Current Price (USD)'].apply(format_price_5dec)
    if 'ATH Price (USD)' in df.columns:
        df['ATH Price (USD)'] = df['ATH Price (USD)'].apply(format_price_5dec)
    if 'Multiply to Price ATH' in df.columns:
        df['Multiply to Price ATH'] = df['Multiply to Price ATH'].apply(
            lambda x: f"{float(x):.2f}" if pd.notnull(x) else "N/A"
        )
    
    return df

def create_percent_bar(percent_str):
    """
    Converts 'Percent from Price ATH' value into an inline HTML progress bar.
    The red bar starts from the RIGHT, showing how far below ATH the price is.
    A minus sign is prefixed to the percentage.
    """
    if not percent_str or percent_str == "N/A":
        return "N/A"
    
    try:
        # Convert to float; if negative, we take the absolute value to get the magnitude.
        val = abs(float(percent_str))
        # If you want to cap at 100%, do: val = min(val, 100.0)

        # We place the bar on the right by using 'float: right;'
        # Add a minus sign before the digits (e.g., -50.44%).
        bar_html = (
            f'<div class="percentage-bar-container">'
            f'<div class="percentage-bar" style="float: right; width: {val}%; background-color: red;">'
            f'-{val:.2f}%</div>'
            '</div>'
        )
        return bar_html
    except:
        return str(percent_str)

def fetch_data_from_google_sheets():
    """Fetch data from the specified Google Sheet and return a DataFrame."""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    
    sheet = client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    return df

def generate_html_table(df):
    """
    1) Keep only the required columns.
    2) Format numeric columns.
    3) Convert 'Percent from Price ATH' into an HTML bar.
    4) Sort by 'Market Cap (USD)' descending if that column exists.
    5) Convert the final DataFrame to HTML (unblurred).
       Blurring & sorting restrictions are handled in JS.
    """
    # Only these columns
    required_cols = [
        'Name',
        'Current Price (USD)',
        'ATH Price (USD)',
        'ATH Date',
        'Percent from Price ATH',
        'Multiply to Price ATH'
    ]
    
    # If 'Market Cap (USD)' is present and you want to sort by it:
    if 'Market Cap (USD)' in df.columns:
        df['Market Cap (USD)'] = pd.to_numeric(df['Market Cap (USD)'], errors='coerce')
        df.sort_values('Market Cap (USD)', ascending=False, inplace=True)
    
    # Filter to required columns, if present
    existing_cols = [col for col in required_cols if col in df.columns]
    if not existing_cols:
        return "<p>No matching columns found in the sheet.</p>"
    
    df = df[existing_cols].copy()
    
    # Format numeric columns
    df = format_values(df)
    
    # Convert 'Percent from Price ATH' to an HTML bar
    if 'Percent from Price ATH' in df.columns:
        df['Percent from Price ATH'] = df['Percent from Price ATH'].apply(create_percent_bar)

    # Convert final DataFrame to HTML
    # No blurring here - that will be handled by the client JS
    html_table = df.to_html(
        index=False,
        classes='crypto-table display',
        border=0,
        escape=False,   # so the bar HTML is not escaped
        table_id='cryptoTable'
    )
    return html_table

def generate_html_page(table_html):
    """
    Returns the complete HTML page, including:
      - A password box
      - Table initially with:
          - 1) row #21 and onward blurred
          - 2) no user sorting allowed
        All done in JS. After correct password, everything is unblurred & sorting is enabled.
    """
    styles = """
    <style>
        body {
            background-color: black;
            color: #f2f2f2;
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        .password-section {
            margin-bottom: 30px;
            text-align: center;
        }
        .password-section input {
            padding: 10px;
            width: 220px;
            border: 1px solid #444;
            border-radius: 4px;
            background-color: #333;
            color: #f2f2f2;
        }
        .password-section button {
            padding: 10px 20px;
            margin-left: 10px;
            border: none;
            border-radius: 4px;
            background-color: #555;
            color: #f2f2f2;
            cursor: pointer;
        }
        .password-section button:hover {
            background-color: #777;
        }
        .crypto-table-container {
            margin: 0 auto;
            width: 90%;
        }
        .crypto-table {
            width: 100%;
            border-collapse: collapse;
            margin: 0 auto;
            min-width: 600px;
        }
        .crypto-table th, .crypto-table td {
            border: 1px solid #444;
            padding: 12px 15px;
            text-align: center;
        }
        .crypto-table th {
            background-color: #333;
        }
        .crypto-table tr:nth-child(even) {
            background-color: #1a1a1a;
        }
        .crypto-table tr:nth-child(odd) {
            background-color: #2a2a2a;
        }
        .crypto-table tr:hover {
            background-color: #555;
        }
        /* Our blur class */
        .blurred-row {
            filter: blur(5px);
            transition: filter 0.3s ease;
        }
        /* Percentage bar container */
        .percentage-bar-container {
            position: relative;
            background-color: #555;
            height: 20px;
            width: 100px;
            margin: 0 auto;
            border-radius: 3px;
            overflow: hidden;
        }
        .percentage-bar {
            height: 100%;
            text-align: center;
            color: white;
            border-radius: 3px;
            line-height: 20px;
            font-size: 12px;
        }
        /* Overriding DataTables elements to keep text white */
        .dataTables_wrapper .dataTables_filter input,
        .dataTables_wrapper .dataTables_length select,
        .dataTables_wrapper .dataTables_info,
        .dataTables_wrapper .dataTables_paginate {
            color: #f2f2f2;
        }
        .dataTables_wrapper .dataTables_filter label,
        .dataTables_wrapper .dataTables_length label {
            color: #f2f2f2;
        }
    </style>
    """

    scripts = """
    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <!-- DataTables -->
    <link rel="stylesheet" type="text/css"
          href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css"/>
    <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>

    <script>
        // We'll manage two DataTables states:
        // 1) ordering = false before unlock
        // 2) ordering = true after unlock
        var table;
        var isUnlocked = false;

        function blurRowsIfLocked() {
            if (!isUnlocked) {
                // Blur row #21 and onward
                var rows = $('#cryptoTable tbody tr');
                rows.removeClass('blurred-row');
                for (var i = 20; i < rows.length; i++) {
                    $(rows[i]).addClass('blurred-row');
                }
            }
        }

        function unlockRows() {
            var password = document.getElementById('crypto-password').value;
            if (password === 'cryptoath') {
                isUnlocked = true;
                // Unblur all rows
                $('#cryptoTable tbody tr').removeClass('blurred-row');

                // Destroy the old table (with no ordering)
                table.destroy();

                // Re-initialize DataTable WITH ordering enabled
                table = $('#cryptoTable').DataTable({
                    paging: false,
                    info: false,
                    ordering: true,
                    searching: false,
                    order: []
                });
            } else {
                alert('Incorrect Password. Please try again.');
            }
        }

        $(document).ready(function() {
            // Initialize DataTable with ordering disabled
            table = $('#cryptoTable').DataTable({
                paging: false,
                info: false,
                ordering: false,
                searching: false,
                order: []
            });

            // On each draw (including initial), blur if locked
            table.on('draw', function() {
                blurRowsIfLocked();
            });

            // Initially blur (in case there's no "draw" event)
            blurRowsIfLocked();
        });
    </script>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Crypto Data Table</title>
      {styles}
    </head>
    <body>
      <h2 style="text-align:center;">Cryptocurrency Prices</h2>

      <div class="password-section">
        <label for="crypto-password">Enter Password to View All Rows & Enable Sorting:</label><br>
        <input type="password" id="crypto-password" placeholder="Enter password">
        <button onclick="unlockRows()">Unlock</button>
      </div>

      <div class="crypto-table-container">
        {table_html}
      </div>

      {scripts}
    </body>
    </html>
    """
    return html

def generate_crypto_table_html():
    """
    Main function to:
      1) Fetch DataFrame from Google Sheets
      2) Keep only desired columns, format them, generate 'Percent from ATH' bars
      3) Sort by Market Cap if present
      4) Convert to HTML (no blur done here)
      5) Build final page with JS-driven blur & locked sorting
      6) Save to 'crypto_table.html'
    """
    df = fetch_data_from_google_sheets()
    table_html = generate_html_table(df)
    full_html = generate_html_page(table_html)

    with open("crypto_table.html", "w", encoding="utf-8") as f:
        f.write(full_html)

    print("HTML table generated and saved to crypto_table.html")

def main():
    try:
        generate_crypto_table_html()
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
