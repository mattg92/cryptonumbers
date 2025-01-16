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

    # Define CSS for the table and blurred rows
    styles = """
    <style>
        .crypto-table {
            width: 100%;
            border-collapse: collapse;
        }
        .crypto-table th, .crypto-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: center;
        }
        .crypto-table th {
            background-color: #f2f2f2;
        }
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
            padding: 8px;
            width: 200px;
        }
        .password-section button {
            padding: 8px 16px;
        }
    </style>
    """

    # Convert DataFrame to HTML
    html_table = df_limited.to_html(index=False, classes='crypto-table', border=0)

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
        {html_table}
        
        <!-- Password Protection Section -->
        <div class="password-section">
            <label for="crypto-password">Enter Password to View All Rows:</label><br>
            <input type="password" id="crypto-password" placeholder="Enter password">
            <button onclick="unlockRows()">Unlock</button>
        </div>
        
        <script>
            function unlockRows() {{
                var password = document.getElementById('crypto-password').value;
                var correctPassword = '{PASSWORD}'; // Replace with your desired password
                
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
    # Fetch data from Google Sheets
    df = fetch_data_from_google_sheets()

    # Generate HTML table
    generate_html_table(df, limit=20)

if __name__ == "__main__":
    main()
