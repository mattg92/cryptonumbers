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

def format_market_cap(x):
    """
    Formats Market Cap (USD) with commas and dollar sign.
    """
    if pd.isnull(x):
        return "N/A"
    try:
        value = float(x)
        return f"${value:,.0f}"
    except:
        return str(x)

def format_values(df):
    """
    Formats numerical columns:
      - Current Price (USD) & ATH Price (USD): 2 decimals if >= $1, 6 decimals if < $1
      - Multiply to Price ATH: 2 decimals
      - Converts 'ATH Date' to YYYY-MM-DD
      - Market Cap (USD): formatted with commas and dollar sign
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
    if 'Market Cap (USD)' in df.columns:
        df['Market Cap (USD)'] = df['Market Cap (USD)'].apply(format_market_cap)
    
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
         'ATH Date','Percent from Price ATH','Multiply to Price ATH','Market Cap (USD)', 'Rank']
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
        'Multiply to Price ATH',
        'Market Cap (USD)'
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
      - A top filter section with a Name filter and an "Other filters" button
      - A popup section for additional filters (with "from" and "to" fields for remaining columns)
      - A scrollable table container and last-updated note at the bottom
      - Column sorting enabled with DataTables
    """
    styles = """
    <style>
        body {
            background-color: black;
            color: #f2f2f2;
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        
        /* Filter controls */
        #filterControls {
            margin-bottom: 10px;
            text-align: center;
        }
        #filterControls input, #filterControls button {
            padding: 8px;
            font-size: 14px;
            margin: 0 5px;
        }
        
        /* Popup for other filters */
        #otherFiltersPopup {
            display: none;
            position: fixed;
            top: 20%;
            left: 50%;
            transform: translateX(-50%);
            background-color: #333;
            padding: 20px;
            border: 1px solid #444;
            border-radius: 5px;
            z-index: 1000;
        }
        #otherFiltersPopup h4 {
            margin-top: 0;
            text-align: center;
        }
        #otherFiltersPopup input {
            padding: 5px;
            width: 80px;
            margin: 0 5px;
        }
        #otherFiltersPopup button {
            padding: 5px 10px;
            background-color: #555;
            color: #f2f2f2;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            margin: 5px;
        }
        #otherFiltersPopup button:hover {
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
            text-align: center;
            position: relative;
        }
        .crypto-table thead th {
            text-align: center !important;
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
        
        /* Last updated text */
        .last-updated-container {
            text-align: center;
            margin-top: 10px;
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
    $(document).ready(function() {
        // Initialize DataTable
        var table = $('#cryptoTable').DataTable({
            paging: true,
            pageLength: 30, // Display 30 rows per page
            info: false,
            ordering: true,
            searching: true,
            dom: '<"top"p>rt<"bottom"p><"clear">',
            order: []
        });

        // Name filter: dynamically filter "Name" column (assumed to be the first column)
        $("#nameFilter").on("keyup", function() {
            table.column(0).search(this.value).draw();
        });

        // Populate the other filters popup with inputs for each column except "Name"
        $('#cryptoTable thead th').each(function(index) {
            var title = $(this).text().trim();
            if (title !== "Name") {
                $('#otherFiltersContent').append(
                    '<div class="filter-group" data-column="'+title+'" style="margin-bottom: 10px;">' +
                    '<label>'+title+': </label> ' +
                    'From: <input type="text" class="from"> ' +
                    'To: <input type="text" class="to">' +
                    '</div>'
                );
            }
        });

        // Toggle other filters popup
        $("#otherFiltersBtn").on("click", function() {
            $("#otherFiltersPopup").toggle();
        });

        $("#applyOtherFilters").on("click", function(){
            table.draw();
            $("#otherFiltersPopup").hide();
        });
        $("#closeOtherFilters").on("click", function(){
            $("#otherFiltersPopup").hide();
        });

        // Custom filtering function for other filters
        $.fn.dataTable.ext.search.push(
            function(settings, data, dataIndex) {
                var pass = true;
                $("#otherFiltersContent .filter-group").each(function() {
                    var columnName = $(this).data("column");
                    // Get the column index by matching header text
                    var colIndex = $('#cryptoTable thead th').filter(function(){
                        return $(this).text().trim() === columnName;
                    }).index();
                    var fromVal = $(this).find('.from').val();
                    var toVal = $(this).find('.to').val();
                    var cellVal = data[colIndex] || "";
                    // Remove HTML tags if any (e.g., from the percent bar)
                    cellVal = cellVal.replace(/<[^>]*>?/gm, '');
                    
                    // Attempt to parse a number from the cell value
                    var cellNum = parseFloat(cellVal.replace(/[^0-9\\.-]+/g, ''));
                    var isNumeric = !isNaN(cellNum);
                    
                    if (isNumeric) {
                        var fromNum = parseFloat(fromVal);
                        var toNum = parseFloat(toVal);
                        if (!isNaN(fromNum) && cellNum < fromNum) {
                            pass = false;
                        }
                        if (!isNaN(toNum) && cellNum > toNum) {
                            pass = false;
                        }
                    } else {
                        // For non-numeric values, use lexicographical filtering (case-insensitive)
                        if (fromVal && cellVal.toLowerCase() < fromVal.toLowerCase()) {
                            pass = false;
                        }
                        if (toVal && cellVal.toLowerCase() > toVal.toLowerCase()) {
                            pass = false;
                        }
                    }
                });
                return pass;
            }
        );
    });
    </script>
    """

    # Build final HTML with filter controls on top and the other filters popup.
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Crypto Data Table</title>
      {styles}
    </head>
    <body>
      <!-- Filter Controls -->
      <div id="filterControls">
          <input type="text" id="nameFilter" placeholder="Filter by coin name">
          <button id="otherFiltersBtn">Other filters</button>
      </div>

      <!-- Popup for Other Filters -->
      <div id="otherFiltersPopup">
          <h4>Other Filters</h4>
          <div id="otherFiltersContent"></div>
          <div style="text-align: center; margin-top: 10px;">
            <button id="applyOtherFilters">Apply</button>
            <button id="closeOtherFilters">Close</button>
          </div>
      </div>

      <!-- Table Container -->
      <div class="crypto-table-container">
        {table_html}
      </div>

      <!-- Last Updated -->
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
      5) Adds a dynamic Name filter and a popup for other filters (with numeric filtering)
      6) Adds a last-updated line
      7) Saves to 'crypto_table.html'
    """
    df = fetch_data_from_google_sheets()

    # Generate the table HTML
    table_html = generate_html_table(df)
    
    # Extract last updated info
    last_updated_str = extract_last_updated_info(df)

    # Build final page with filters, table, and last-updated info
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
