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
    # Define the scope
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    # Authenticate using the service account file
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    
    # Open the spreadsheet and worksheet
    sheet = client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)
    
    # Get all records
    records = sheet.get_all_records()
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    
    return df

def format_values(df):
    """
    Formats numerical columns:
    - Current Price (USD) and ATH Price (USD): 5 decimal places
    - Market Cap (USD) and ATH Market Cap (USD): in millions
    """
    # Define formatting functions
    def format_price(x):
        return f"${x:,.5f}" if pd.notnull(x) else "N/A"
    
    # Apply formatting
    if 'Current Price (USD)' in df.columns:
        df['Current Price (USD)'] = df['Current Price (USD)'].apply(format_price)
    if 'ATH Price (USD)' in df.columns:
        df['ATH Price (USD)'] = df['ATH Price (USD)'].apply(format_price)
    if 'Market Cap (USD)' in df.columns:
        df['Market Cap (USD)'] = df['Market Cap (USD)'] / 1_000_000
    if 'ATH Market Cap (USD)' in df.columns:
        df['ATH Market Cap (USD)'] = df['ATH Market Cap (USD)'] / 1_000_000
    
    return df

def generate_html_table(df, columns):
    """
    Generates HTML for the table with specified columns.
    """
    # Sort DataFrame by Market Cap
    df = df.sort_values(by='Market Cap (USD)', ascending=False).reset_index(drop=True)
    
    # Select required columns
    df = df[columns].copy()
    
    # Format DataFrame
    df = format_values(df)
    
    # Convert to HTML
    html_table = df.to_html(index=False, classes='crypto-table', border=0, escape=False)
    
    # Process with BeautifulSoup to add 'blurred-row' class beyond first 20 rows
    soup = BeautifulSoup(html_table, 'html.parser')
    rows = soup.find_all('tr')[21:]  # +1 for header, first 20 data rows
    for row in rows:
        row['class'] = row.get('class', []) + ['blurred-row']
    
    return str(soup)

def generate_html_content(tab1_html, tab2_html):
    """
    Generates the complete HTML content with two tabs and password protection
    """
    styles = """
    <style>
        body {
            background-color: black;
            color: #f2f2f2;
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        /* Tab styles */
        .tab {
            overflow: hidden;
            border-bottom: 1px solid #444;
        }

        .tab button {
            background-color: inherit;
            border: none;
            outline: none;
            cursor: pointer;
            padding: 14px 16px;
            transition: background-color 0.3s;
            color: #f2f2f2;
            font-size: 17px;
        }

        .tab button:hover {
            background-color: #575757;
        }

        .tab button.active {
            background-color: #333;
        }

        /* Table container for responsiveness */
        .crypto-table-container {
            overflow-x: auto;
            margin-left: 10%;
            margin-right: 10%;
            overflow-y: auto;
            max-height: 600px;
        }

        /* Table styling */
        .crypto-table {
            width: 80%;
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
        /* Password section styles */
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
        /* Responsive Font Sizes */
        @media (max-width: 768px) {
            .crypto-table th, .crypto-table td {
                padding: 10px 12px;
                font-size: 14px;
            }
            .tab button {
                padding: 10px 12px;
                font-size: 15px;
            }
        }
        @media (max-width: 480px) {
            .crypto-table th, .crypto-table td {
                padding: 8px 10px;
                font-size: 12px;
            }
            .tab button {
                padding: 8px 10px;
                font-size: 13px;
            }
        }

    </style>
    """

    scripts = f"""
    <script src="https://code.jquery.com/jquery-3.5.1.js"></script>
    <script>
        // Tab functionality
        function openTab(evt, tabName) {{
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tabcontent");
            for (i = 0; i < tabcontent.length; i++) {{
                tabcontent[i].style.display = "none";
            }}
            tablinks = document.getElementsByClassName("tablinks");
            for (i = 0; i < tablinks.length; i++) {{
                tablinks[i].className = tablinks[i].className.replace(" active", "");
            }}
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
        }}

        // Set default tab
        document.addEventListener("DOMContentLoaded", function() {{
            document.getElementsByClassName("tablinks")[0].click();
        }});

        // Password functionality
        function unlockRows() {{
            var password = document.getElementById('crypto-password').value;
            var correctPassword = 'unlock';
            
            if(password === correctPassword) {{
                var blurredRows = document.querySelectorAll('.blurred-row');
                blurredRows.forEach(function(row) {{
                    row.classList.remove('blurred-row');
                }});
            }} else {{
                alert('Incorrect Password. Please try again.');
            }}
        }}
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
        <h2 style="text-align:center;">Cryptocurrency Data</h2>
        
        <!-- Password Section -->
        <div class="password-section">
            <label for="crypto-password">Enter Password to View All Rows:</label><br>
            <input type="password" id="crypto-password" placeholder="Enter password">
            <button onclick="unlockRows()">Unlock</button>
        </div>
        
        <!-- Tab buttons -->
        <div class="tab">
            <button class="tablinks" onclick="openTab(event, 'Tab1')">Price Data</button>
            <button class="tablinks" onclick="openTab(event, 'Tab2')">Market Cap Data (M)</button>
        </div>
        
        <!-- Tab 1 Content -->
        <div id="Tab1" class="tabcontent">
            <div class="crypto-table-container">
                {tab1_html}
            </div>
        </div>
        
        <!-- Tab 2 Content -->
        <div id="Tab2" class="tabcontent">
            <div class="crypto-table-container">
                {tab2_html}
            </div>
        </div>
        
        {scripts}
    </body>
    </html>
    """

    return html_content

def generate_crypto_table_html():
    # Fetch data from Google Sheets
    df = fetch_data_from_google_sheets()
    
    # Sort DataFrame by Market Cap
    df = df.sort_values(by='Market Cap (USD)', ascending=False).reset_index(drop=True)
    
    # Generate HTML tables for both tabs
    tab1_html = generate_html_table(df, ['Name', 'Current Price (USD)', 'ATH Price (USD)', 'ATH Date', 'Last Updated'])
    tab2_html = generate_html_table(df, ['Name', 'Current Price (USD)', 'Market Cap (USD)', 'ATH Market Cap (USD)', 'ATH Market Cap Date', 'Last Updated'])
    
    # Generate complete HTML content
    full_html = generate_html_content(tab1_html, tab2_html)
    
    # Write to HTML file
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
