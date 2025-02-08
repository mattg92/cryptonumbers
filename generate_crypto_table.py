import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
from bs4 import BeautifulSoup

# Environment variables
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME')
WORKSHEET_NAME = os.getenv('WORKSHEET_NAME')

def extract_last_updated_info(df):
    """
    Returns the latest 'Last Updated' value from the DataFrame (if present),
    with any trailing 'Z' removed. Otherwise returns "N/A".
    """
    if 'Last Updated' not in df.columns:
        return "N/A"
    last_val = df['Last Updated'].max()
    if pd.isnull(last_val):
        return "N/A"
    return str(last_val).replace("Z", "")

def format_ath_date(x):
    """
    Parses a date/time string into YYYY-MM-DD format.
    If invalid or missing, returns 'N/A'.
    """
    if pd.isnull(x):
        return "N/A"
    try:
        dt = pd.to_datetime(x, errors='coerce', utc=True)
        if pd.isnull(dt):
            return "N/A"
        return dt.strftime("%Y-%m-%d")
    except:
        return "N/A"

def format_price(x):
    """
    Rounds Current Price (USD) and ATH Price (USD) to two decimal places if the value is 
    higher than or equal to 1 dollar, and rounds to six decimal places if the price is lower than 1 dollar.
    """
    if pd.isnull(x):
        return "N/A"
    try:
        value = float(x)
        if value >= 1:
            return f"${value:,.2f}"
        else:
            return f"${value:,.6f}"
    except:
        return str(x)

def format_values(df):
    """
    Formats numerical columns:
      - Current Price (USD) & ATH Price (USD): 2 decimals if >= $1, 6 decimals if < $1
      - Multiply to Price ATH: 2 decimals
      - Converts 'ATH Date' to YYYY-MM-DD
    """
    # Format numeric columns if they exist
    if 'Current Price (USD)' in df.columns:
        df['Current Price (USD)'] = df['Current Price (USD)'].apply(format_price)
    if 'ATH Price (USD)' in df.columns:
        df['ATH Price (USD)'] = df['ATH Price (USD)'].apply(format_price)
    if 'Multiply to Price ATH' in df.columns:
        df['Multiply to Price ATH'] = df['Multiply to Price ATH'].apply(
            lambda x: f"{float(x):.2f}" if pd.notnull(x) else "N/A"
        )
    if 'ATH Date' in df.columns:
        df['ATH Date'] = df['ATH Date'].apply(format_ath_date)
    
    return df
    

def create_percent_bar(percent_str):
    """
    Converts 'Percent from Price ATH' value into a horizontal bar, anchored to
    the right with a minus sign. The percentage text is pinned on the right side
    within the gray bar, ensuring it's always visible.
    """
    if not percent_str or percent_str == "N/A":
        return "N/A"

    try:
        val = abs(float(percent_str))  # e.g., 31.85 for -31.85

        # Single-line HTML to avoid literal \n characters
        bar_html = (
            '<div style="position: relative; width: 100px; height: 20px; '
            'background-color: #555; border-radius: 3px; overflow: hidden; margin: 0 auto; display: block;">'
              f'<div style="position: absolute; right: 0; top: 0; bottom: 0; '
              f'width: {val}%; background-color: red; border-radius: 3px;">'
              '</div>'
              '<!-- Text overlay -->'
              '<div style="position: absolute; right: 5px; z-index: 2; color: #fff; font-size: 12px; '
              'line-height: 20px; padding-right: 5px; text-align: right; width: 100%;">'
                f'-{val:.2f}%'
              '</div>'
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
    1) Keep only the required columns:
        ['Name','Current Price (USD)','ATH Price (USD)',
         'ATH Date','Percent from Price ATH','Multiply to Price ATH']
    2) Format numeric columns, parse 'ATH Date'
    3) Convert 'Percent from Price ATH' to an HTML bar
    4) Sort by 'Market Cap (USD)' descending if that column exists
    5) Return HTML (no blur or disabling sorting here - all in JS)
    """
    # The columns we actually want in the final table:
    required_cols = [
        'Name',
        'Rank',
        'Current Price (USD)',
        'ATH Price (USD)',
        'ATH Date',
        'Percent from Price ATH',
        'Multiply to Price ATH'
    ]
    
    # If 'Market Cap (USD)' is present, we can sort by it descending
    if 'Market Cap (USD)' in df.columns:
        df['Market Cap (USD)'] = pd.to_numeric(df['Market Cap (USD)'], errors='coerce')
        df.sort_values('Market Cap (USD)', ascending=False, inplace=True)
    
    # Filter to only the required columns if they exist
    existing_cols = [col for col in required_cols if col in df.columns]
    if not existing_cols:
        return "<p>No matching columns found in the sheet.</p>"
    
    df = df[existing_cols].copy()
    
    # Apply formatting (numbers, ATH date)
    df = format_values(df)
    
    # Convert 'Percent from Price ATH' to bar
    if 'Percent from Price ATH' in df.columns:
        df['Percent from Price ATH'] = df['Percent from Price ATH'].apply(create_percent_bar)

    # Convert final DataFrame to HTML
    html_table = df.to_html(
        index=False,
        classes='crypto-table display',
        border=0,
        escape=False,  # so the bar HTML isn't escaped
        table_id='cryptoTable'
    )
    return html_table

def generate_html_page(table_html, last_updated_str):
    """
    Returns the complete HTML page, including:
      - A password prompt: "enter password to view all coins"
      - A scrollable container (~21 rows visible)
      - Column sorting disabled until unlocked
      - Rows #22+ blurred until unlock
      - A 'Data last updated: ...' note at the bottom
    """
    styles = """
    <style>
        body {
            background-color: black;
            color: #f2f2f2;
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        /* Password prompt */
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
        
        /* Table container with scrolling */
        .crypto-table-container {
            margin: 0 auto;
            width: 90%;
            max-height: 800px; /* approximate for ~21 rows visible */
            overflow-y: auto;
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
            text-align: center; /* center columns' names & data */
        }

        /* If DataTables overrides the header, use this: */
        .crypto-table thead th {
            text-align: center !important;
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
        
        /* Row blur */
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
            overflow: visible; /* ensure we see the text fully */
        }
        .percentage-bar {
            height: 100%;
            color: white;
            border-radius: 3px;
            line-height: 20px;
            font-size: 12px;
        }

        /* Overriding DataTables elements to keep text white (when we re-enable sorting) */
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
        
        /* Last-updated note */
        .last-updated {
            margin: 0 auto;
            width: 90%;
            text-align: left;
            margin-top: 20px;
            font-style: italic;
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
    var table;
    var isUnlocked = false;

    // Blur row #22 onward if locked
    function blurRowsIfLocked() {
        if (!isUnlocked) {
            var rows = $('#cryptoTable tbody tr');
            rows.removeClass('blurred-row');
            var startIndex = table.page.info().start;
            var endIndex = table.page.info().end;
            // Blur rows based on their global index
            for (var i = 0; i < rows.length; i++) {
                if ((startIndex + i) >= 20) {
                    $(rows[i]).addClass('blurred-row');
                }
            }
        }
    }

    // Password check
    function unlockRows() {
        var password = document.getElementById('crypto-password').value;
        if (password === 'cryptoath') {
            isUnlocked = true;
            // Unblur everything
            $('#cryptoTable tbody tr').removeClass('blurred-row');
            // Destroy old table
            table.destroy();
            // Re-init table with ordering enabled
            table = $('#cryptoTable').DataTable({
                paging: true,
                pageLength: 30, // Set pagination to display 30 rows per page
                info: false,
                ordering: true,
                searching: false,
                dom: '<"top"p>rt<"bottom"p><"clear">',
                order: []
            });
        } else {
            alert('Incorrect password. Please try again.');
        }
    }

    $(document).ready(function() {
        // Start with ordering and pagination disabled
        table = $('#cryptoTable').DataTable({
            paging: true,
            pageLength: 30, // Set pagination to display 50 rows per page
            info: false,
            ordering: false,
            searching: false,
            dom: '<"top"p>rt<"bottom"p><"clear">',
            order: []
        });
        // After each draw, blur if locked
        table.on('draw', function() {
            blurRowsIfLocked();
        });
        // Initial blur
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
      <!-- No title, as requested -->
      <div class="password-section">
        <label for="crypto-password">enter password to view all coins</label><br>
        <input type="password" id="crypto-password" placeholder="Enter password">
        <button onclick="unlockRows()">Unlock</button>
      </div>

      <div class="crypto-table-container">
        {table_html}
      </div>

      <!-- Short sentence under the table about last updated time -->
      <div class="last-updated-container">
        <p class="last-updated">Data last updated: {last_updated_str} UTC</p>
      </div>
      
      {scripts}
    </body>
    </html>
    """
    return html

def generate_crypto_table_html():
    """
    Main function that:
      1) Fetches data from Google Sheets
      2) Filters & formats columns, including a right-aligned percentage bar
      3) Sorts by Market Cap if present
      4) Creates an HTML table
      5) Blurs rows #22+ and disables sorting until correct password is entered
      6) Adds a last-updated line
      7) Saves to 'crypto_table.html'
    """
    df = fetch_data_from_google_sheets()

    # Generate the table HTML
    table_html = generate_html_table(df)
    
    # Extract last updated info
    last_updated_str = extract_last_updated_info(df)

    # Build final page with password lock, blur logic, scrolling, etc.
    full_html = generate_html_page(table_html, last_updated_str)

    # Write to file
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
