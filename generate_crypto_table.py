import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
from datetime import datetime

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

def generate_html_table(df, limit=20):
    # Limit to first 'limit' rows
    df_limited = df.head(limit)

    # Define CSS for the table and responsiveness
    styles = """
    <style>
        body {
            background-color: black;
            color: #f2f2f2;
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        .crypto-table-container {
            overflow-x: auto;
        }
        .crypto-table {
            width: 100%;
            border-collapse: collapse;
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
        /* Responsive Font Sizes */
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
    </style>
    """

    # Convert DataFrame to HTML
    html_table = df_limited.to_html(index=False, classes='crypto-table', border=0, escape=False)

    # Add classes to table rows beyond the limited rows to apply blur
    # Assuming you want to display only the top 'limit' rows and blur the rest
    # Fetch all records again to handle additional rows
    total_rows = df.shape[0]
    additional_rows = total_rows - limit
    if additional_rows > 0:
        # Re-fetch all records to include blurred rows
        df_all = fetch_data_from_google_sheets()
        # Convert to HTML with all rows
        html_full_table = df_all.to_html(index=False, classes='crypto-table', border=0, escape=False)
        # Inject 'blurred-row' class to rows beyond the limit
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_full_table, 'html.parser')
        rows = soup.find_all('tr')[limit+1:]  # +1 to skip the header row
        for row in rows:
            row['class'] = row.get('class', []) + ['blurred-row']
        
        # Update the HTML table
        html_table = str(soup)

    # Complete HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Crypto Data Table</title>
        {styles}
    </head>
    <body>
        <h2 style="text-align:center;">Cryptocurrency Data (Top {limit})</h2>
        <div class="crypto-table-container">
            {html_table}
        </div>
        
        <!-- Password Protection Section -->
        <div class="password-section">
            <label for="crypto-password">Enter Password to View All Rows:</label><br>
            <input type="password" id="crypto-password" placeholder="Enter password">
            <button onclick="unlockRows()">Unlock</button>
        </div>
        
        <script>
            function unlockRows() {{
                var password = document.getElementById('crypto-password').value;
                var correctPassword = '{PASSWORD}';
                
                if(password === correctPassword) {{
                    var blurredRows = document.querySelectorAll('.blurred-row');
                    blurredRows.forEach(function(row) {{
                        row.classList.remove('blurred-row');
                    }});
                    alert('Access Granted!');
                }} else {{
                    alert('Incorrect Password. Please try again.');
                }}
            }}
        </script>
    </body>
    </html>
    """

    # Write to HTML file
    with open('crypto_table.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML table generated and saved to crypto_table.html")

def main():
    try:
        # Fetch data from Google Sheets
        df = fetch_data_from_google_sheets()

        # Generate HTML table
        generate_html_table(df, limit=20)
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)

if __name__ == "__main__":
    main()
