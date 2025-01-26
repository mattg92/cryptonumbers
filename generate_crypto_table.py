import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
from bs4 import BeautifulSoup

SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME')
WORKSHEET_NAME = os.getenv('WORKSHEET_NAME')

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
    Convert the DataFrame to an HTML table string (unblurred). 
    We'll blur the rows in JavaScript, not here in Python.
    """
    # Example: Sort by Market Cap descending if present
    if 'Market Cap (USD)' in df.columns:
        df['Market Cap (USD)'] = pd.to_numeric(df['Market Cap (USD)'], errors='coerce')
        df.sort_values('Market Cap (USD)', ascending=False, inplace=True)
    
    # If you only want certain columns, filter them here:
    # required_cols = [...]
    # df = df[required_cols]
    
    # Convert to HTML (no row-blurring here):
    html_table = df.to_html(
        index=False,
        classes='crypto-table display',
        border=0,
        escape=False,      # if you have custom HTML in some cells
        table_id='cryptoTable'
    )
    return html_table

def generate_html_page(table_html):
    """
    Returns the complete HTML page, including DataTables and 
    JS code that blurs all but the first 20 rows on each draw—unless unlocked.
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
        var isUnlocked = false;  // Tracks whether rows are unlocked or not

        // Called after each DataTables draw event to blur rows, if still locked
        function blurRowsIfLocked() {
            if (!isUnlocked) {
                // Select all data rows
                var rows = $('#cryptoTable tbody tr');
                // Remove blur from all, then re-apply it after the 20th row
                rows.removeClass('blurred-row');
                for (var i = 20; i < rows.length; i++) {
                    $(rows[i]).addClass('blurred-row');
                }
            }
        }

        function unlockRows() {
            var password = document.getElementById('crypto-password').value;
            if(password === 'cryptoath') {
                isUnlocked = true;
                // Remove blur from all rows
                $('#cryptoTable tbody tr').removeClass('blurred-row');
            } else {
                alert('Incorrect Password. Please try again.');
            }
        }

        $(document).ready(function() {
            var table = $('#cryptoTable').DataTable({
                paging: false,
                info: false,
                ordering: true,
                searching: false,
                // If you want no initial re-sorting by DataTables,
                // you can specify "order": [] here:
                order: []
            });

            // On every DataTables draw (including the initial),
            // re-check if we should blur rows.
            table.on('draw', function() {
                blurRowsIfLocked();
            });

            // Blur initially
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
        <label for="crypto-password">Enter Password to View All Rows:</label><br>
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
      1) Fetch data from Google Sheets
      2) Convert to HTML (no blurring in Python)
      3) Build a page with JS that blurs all but the first 20 rows
         until the user enters the password 'cryptoath'
      4) Save to 'crypto_table.html'
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
