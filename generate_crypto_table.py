import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
from datetime import datetime
from bs4 import BeautifulSoup

# Configuration from environment variables
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME')
WORKSHEET_NAME = os.getenv('WORKSHEET_NAME')

def fetch_data_from_google_sheets():
    """
    Fetch data from the specified Google Sheets worksheet and return as a DataFrame.
    """
    # Define the scope
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    # Authenticate using the service account file
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    
    # Open the spreadsheet and worksheet
    sheet = client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)
    
    # Get all records (list of dicts)
    records = sheet.get_all_records()
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    return df

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
            return f"${float(x):,.5f}"
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
        # Add a minus sign before the digits.
        bar_html = (
            f'<div class="percentage-bar-container">'
            f'<div class="percentage-bar" style="float: right; width: {val}%; background-color: red;">'
            f'-{val:.2f}%</div>'  # always show minus
            '</div>'
        )
        return bar_html
    except:
        return str(percent_str)

def generate_single_table_html(df):
    """
    Generates HTML for a single table with columns (if present):
      - Name
      - Current Price (USD)
      - ATH Price (USD)
      - ATH Date
      - Percent from Price ATH (rendered as a progress bar)
      - Multiply to Price ATH
    
    Removes 'Last Updated' from the output, if present.
    Sorts by 'Market Cap (USD)' descending at the start (if present).
    Blurs rows after the first 20 until unlocked.
    """
    # 1. If 'Market Cap (USD)' is present, convert to numeric & sort descending
    if 'Market Cap (USD)' in df.columns:
        df['Market Cap (USD)'] = pd.to_numeric(df['Market Cap (USD)'], errors='coerce')
        df.sort_values('Market Cap (USD)', ascending=False, inplace=True)
    
    # 2. Define the columns we actually want to display (do NOT include 'Last Updated')
    required_cols = [
        'Name',
        'Current Price (USD)',
        'ATH Price (USD)',
        'ATH Date',
        'Percent from Price ATH',
        'Multiply to Price ATH'
    ]
    
    existing_cols = [col for col in required_cols if col in df.columns]
    if not existing_cols:
        return "<p>No matching columns found in the sheet.</p>"
    
    # 3. Filter DataFrame to just these columns
    df = df[existing_cols].copy()
    
    # 4. Format numeric columns
    df = format_values(df)
    
    # 5. Convert "Percent from Price ATH" to HTML bars
    if 'Percent from Price ATH' in df.columns:
        df['Percent from Price ATH'] = df['Percent from Price ATH'].apply(create_percent_bar)
    
    # 6. Convert to HTML table
    html_table = df.to_html(
        index=False,
        classes='crypto-table display',
        border=0,
        escape=False,      # so the HTML bar is not escaped
        table_id='cryptoTable'
    )
    
    # 7. Blur rows after the first 20 data rows (+ 1 header => row index 21+)
    soup = BeautifulSoup(html_table, 'html.parser')
    all_rows = soup.find_all('tr')
    blurred_rows = all_rows[21:]  # 0 = header, 1..20 = first 20 data rows
    for row in blurred_rows:
        classes = row.get('class', [])
        row['class'] = classes + ['blurred-row']
    
    return str(soup)

def generate_html_content(table_html):
    """
    Builds the full HTML page:
      - A heading
      - Password box + unlock button (password: 'cryptoath')
      - The table container
      - DataTables for sorting
    """
    styles = """
    <style>
        body {
            background-color: black;
            color: #f2f2f2;
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        
        /* Password section */
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

        /* Table container */
        .crypto-table-container {
            margin: 0 auto;
            width: 90%;
        }

        /* Table styling (DataTables uses 'display' class) */
        .crypto-table {
            width: 100%;
            border-collapse: collapse;
            margin: 0 auto;
            min-width: 600px;
            color: #f2f2f2;
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
        
        /* Blurred rows */
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

        /* DataTables override (to keep text white) */
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

        /* Responsive adjustments */
        @media (max-width: 768px) {
            .crypto-table th, .crypto-table td {
                padding: 10px 12px;
                font-size: 14px;
            }
        }
        @media (max-width: 480px) {
            .crypto-table th, .crypto-table td {
                padding: 8px 10px;
                font-size: 12px;
            }
        }
    </style>
    """
    
    # We'll load jQuery and DataTables from a CDN
    scripts = """
    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <!-- DataTables JS & CSS -->
    <link rel="stylesheet" type="text/css" 
          href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css"/>
    <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>

    <script>
        // Initialize DataTables once the document is ready
        $(document).ready(function() {
            // We disable paging & searching but keep ordering (sorting) enabled
            $('#cryptoTable').DataTable({
                "paging": false,
                "info": false,
                "ordering": true,
                "searching": false
            });
        });

        // Password unlock functionality
        function unlockRows() {
            var password = document.getElementById('crypto-password').value;
            var correctPassword = 'cryptoath';
            
            if(password === correctPassword) {
                var blurredRows = document.querySelectorAll('.blurred-row');
                blurredRows.forEach(function(row) {
                    row.classList.remove('blurred-row');
                });
            } else {
                alert('Incorrect Password. Please try again.');
            }
        }
    </script>
    """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Crypto Data Table</title>
        {styles}
    </head>
    <body>
        <h2 style="text-align:center;">Cryptocurrency Prices</h2>
        
        <!-- Password Section -->
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
    return html_content

def generate_crypto_table_html():
    """
    Main function to:
     1) Fetch data from Google Sheets
     2) Sort by Market Cap (USD) descending if available
     3) Show a single table (20 unblurred rows, rest blurred)
     4) Use password 'cryptoath'
     5) Remove 'Last Updated' column entirely
     6) Place the red bar from the right, prefixed with '-'
    """
    # 1. Fetch DataFrame
    df = fetch_data_from_google_sheets()
    
    # 2. Generate the HTML for our single table
    single_table_html = generate_single_table_html(df)
    
    # 3. Build final HTML
    full_html = generate_html_content(single_table_html)
    
    # 4. Write to an HTML file
    with open('crypto_table.html', 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print("HTML table generated and saved to crypto_table.html")

def main():
    try:
        generate_crypto_table_html()
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)

if __name__ == "__main__":
    main()
