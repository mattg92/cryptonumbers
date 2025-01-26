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
PASSWORD = os.getenv('PASSWORD')

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
    
    # Get all records (as list of dicts)
    records = sheet.get_all_records()
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    return df

def format_values(df):
    """
    Formats numerical columns:
      - Current Price (USD) and ATH Price (USD): 5 decimal places
        (e.g., $1,234.56789)
    """
    def format_price(x):
        if pd.isnull(x):
            return "N/A"
        try:
            return f"${float(x):,.5f}"
        except:
            return str(x)
    
    # Apply formatting if these columns exist
    if 'Current Price (USD)' in df.columns:
        df['Current Price (USD)'] = df['Current Price (USD)'].apply(format_price)
    if 'ATH Price (USD)' in df.columns:
        df['ATH Price (USD)'] = df['ATH Price (USD)'].apply(format_price)
    
    return df

def create_percent_bar(percent_str):
    """
    Creates an HTML-based progress bar using the 'Percent from Price ATH' value.
    - Interprets negative or positive numeric strings as a magnitude (absolute value).
    - Clamps to 100% if desired (optional) or simply uses the raw absolute value.
    - If the cell is empty or invalid, returns "N/A".
    """
    if not percent_str or percent_str == "N/A":
        return "N/A"
    
    try:
        val = abs(float(percent_str))  # 74.3 -> 74.3% (assuming negative means below ATH)
        # If you'd like to cap it at 100%, uncomment the next line:
        # val = min(val, 100.0)
        
        # Create a red bar on a gray container
        bar_html = f"""
        <div class="percentage-bar-container">
          <div class="percentage-bar" style="width: {val}%; background-color: red;">
            {val}%
          </div>
        </div>
        """
        return bar_html
    except:
        return str(percent_str)

def generate_single_table_html(df):
    """
    Generates HTML for a single table with columns:
      Name, Current Price (USD), ATH Price (USD), ATH Date,
      and a progress bar for 'Percent from Price ATH'.
    
    Rows beyond the first 20 will be blurred.
    """
    # We only need these columns (assuming they exist in your sheet)
    required_cols = [
        'Name',
        'Current Price (USD)',
        'ATH Price (USD)',
        'ATH Date',
        'Percent from Price ATH'
    ]
    
    # Filter the DataFrame to include only the required columns (if they exist)
    df = df[[col for col in required_cols if col in df.columns]].copy()
    
    # Format numeric columns
    df = format_values(df)
    
    # Convert "Percent from Price ATH" to an HTML progress bar
    if 'Percent from Price ATH' in df.columns:
        df['Percent from Price ATH'] = df['Percent from Price ATH'].apply(create_percent_bar)
    
    # Convert to HTML
    html_table = df.to_html(
        index=False,
        classes='crypto-table',
        border=0,
        escape=False  # IMPORTANT: so the <div> for the bar isn't escaped
    )
    
    # Use BeautifulSoup to add blurred-row class beyond row 20 (plus 1 header row => row indices 21+ in HTML)
    soup = BeautifulSoup(html_table, 'html.parser')
    # The first row in <tbody> is index 1 in the final HTML (since row 0 is <thead>)
    # So we blur from row 21 onwards => the first 20 data rows remain unblurred.
    all_rows = soup.find_all('tr')
    blurred_rows = all_rows[21:]  # This means: skip the header row (0) plus first 20 data rows => blur from 21 onward
    for row in blurred_rows:
        existing_classes = row.get('class', [])
        row['class'] = existing_classes + ['blurred-row']
    
    return str(soup)

def generate_html_content(table_html):
    """
    Generates the complete HTML content for a single table + password unlock section.
    """
    styles = """
    <style>
        body {
            background-color: black;
            color: #f2f2f2;
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        /* Table container */
        .crypto-table-container {
            overflow-x: auto;
            margin: 0 auto;
            max-height: 600px;
            width: 80%;
        }
        /* Table styling */
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
            color: #f2f2f2;
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
            width: 100px; /* adjust as desired */
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
        
        /* Password section */
        .password-section {
            margin-top: 20px;
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
    scripts = """
    <script src="https://code.jquery.com/jquery-3.5.1.js"></script>
    <script>
        // Password functionality
        function unlockRows() {
            var password = document.getElementById('crypto-password').value;
            var correctPassword = 'unlock';
            
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
    Main function:
     1) Fetch data from Google Sheets
     2) Create a single table with columns:
        Name, Current Price (USD), ATH Price (USD), ATH Date,
        and a red bar for "Percent from Price ATH"
     3) Save to 'crypto_table.html'
    """
    # 1. Fetch DataFrame from your Google Sheets
    df = fetch_data_from_google_sheets()
    
    # 2. Create single-table HTML (with blurred rows after 20th)
    single_table_html = generate_single_table_html(df)
    
    # 3. Generate the final HTML (including styles/scripts)
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
