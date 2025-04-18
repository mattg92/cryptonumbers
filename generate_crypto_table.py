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
    if 'Market Cap ATH (USD)' in df.columns:
        df['Market Cap ATH (USD)'] = df['Market Cap ATH (USD)'].apply(format_market_cap)    
    
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

def generate_mc_table_html(df):
    required_cols = [
        'Name','Rank','Current Price (USD)','Market Cap (USD)',
        'Market Cap ATH (USD)','Percent from MC ATH','Multiply to MC ATH'
    ]
    if 'Market Cap (USD)' in df.columns:
        df['Market Cap (USD)'] = pd.to_numeric(df['Market Cap (USD)'], errors='coerce')
        df.sort_values('Market Cap (USD)', ascending=False, inplace=True)
    df_mc = df[[c for c in required_cols if c in df.columns]].copy()
    df_mc['Market Cap ATH (USD)'] = pd.to_numeric(df_mc['Market Cap ATH (USD)'], errors='coerce')
    df_mc = df_mc[df_mc['Market Cap ATH (USD)'] > 0]
    df_mc = format_values(df_mc)
    if 'Percent from MC ATH' in df_mc.columns:
        df_mc['Percent from MC ATH'] = df_mc['Percent from MC ATH'].apply(create_percent_bar)
    return df_mc.to_html(
        index=False, classes='crypto-table display', border=0,
        escape=False, table_id='mcCryptoTable'
    )


def generate_html_page(main_html, mc_html, last_updated_str):
    # Use original styles including filter controls and other filters popup
    styles = """
    <style>
        body { background-color: black; color: #f2f2f2; font-family: Arial, sans-serif; margin: 20px; }
        /* 1) Hide all tab contents by default */
          .tabcontent {
            display: none;
          }

          /* 2) Show the main (Coin Price) tab on load */
          #mainTab {
            display: block;
          }
        /* Filter controls */
        #filterControls { margin-bottom: 10px; text-align: center; }
        #filterControls input, #filterControls button { padding: 8px; font-size: 14px; margin: 0 5px; }
        /* Tab controls styled like filter controls */
        .tab { margin-bottom: 10px; text-align: center; }
        .tab button { padding: 8px; font-size: 14px; margin: 0 5px; }
        .tab button.active { background-color: #555; }
        /* Popup for other filters */
        #otherFiltersPopup { display: none; position: fixed; top: 20%; left: 50%; transform: translateX(-50%); background-color: #333; padding: 20px; border: 1px solid #444; border-radius: 5px; z-index: 1000; }
        #otherFiltersPopup h4 { margin-top: 0; text-align: center; }
        #otherFiltersPopup input { padding: 5px; width: 80px; margin: 0 5px; }
        #otherFiltersPopup button { padding: 5px 10px; background-color: #555; color: #f2f2f2; border: none; border-radius: 3px; cursor: pointer; margin: 5px; }
        #otherFiltersPopup button:hover { background-color: #777; }
        /* Table container with scrolling */
        .crypto-table-container { margin: 0 auto; width: 90%; max-height: 800px; overflow-y: auto; }
        .crypto-table { width: 100%; border-collapse: collapse; margin: 0 auto; min-width: 600px; }
        .crypto-table th, .crypto-table td { border: 1px solid #444; padding: 12px 15px; text-align: center; position: relative; }
        .crypto-table thead th { text-align: center !important; background-color: #333; }
        .crypto-table tr:nth-child(even) { background-color: #1a1a1a; }
        .crypto-table tr:nth-child(odd) { background-color: #2a2a2a; }
        .crypto-table tr:hover { background-color: #555; }
        /* Last updated text */
        .last-updated-container { text-align: center; margin-top: 10px; }
    </style>
    
    """
    scripts = """
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css"/>
    <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
    <script>
$(document).ready(function() {
    // 1) Initialize both tables with paging, searching, etc.
    $('#cryptoTable, #mcCryptoTable').each(function() {
        $(this).DataTable({
            paging:      true,
            pageLength:  30,
            info:        false,
            ordering:    true,
            searching:   true,
            dom:         '<"top"p>rt<"bottom"p><"clear">',
            order:       []
        });
    });

    // 2) Name filter (text input filters column 0 on both tables)
    $('#nameFilter').on('keyup', function() {
        var val = this.value;
        $('#cryptoTable').DataTable().column(0).search(val).draw();
        $('#mcCryptoTable').DataTable().column(0).search(val).draw();
    });

    // 3) Build the “other filters” popup dynamically
    const addedFilters = new Set(); // Track added filters to prevent duplicates
    ['cryptoTable','mcCryptoTable'].forEach(function(id) {
        $('#' + id + ' thead th').each(function() {
            var title = $(this).text().trim();

            // Skip duplicate filters and "ATH Date"
            if (addedFilters.has(title) || title === 'ATH Date') {
                return;
            }
            addedFilters.add(title);

            // Add filter input group for valid columns
            $('#otherFiltersContent').append(
              '<div class="filter-group" data-column="' + title + '" style="margin-bottom:10px;">' +
                '<label>' + title + ':</label> ' +
                'From: <input type="text" class="from"> ' +
                'To: <input type="text" class="to">' +
              '</div>'
            );
        });
    });

    // 4) Show/hide the popup
    $('#otherFiltersBtn').click(function() {
        $('#otherFiltersPopup').toggle();
    });
    $('#applyOtherFilters').click(function() {
        $('#cryptoTable').DataTable().draw();
        $('#mcCryptoTable').DataTable().draw();
        $('#otherFiltersPopup').hide();
    });
    $('#closeOtherFilters').click(function(){
        $('#otherFiltersPopup').hide();
    });

    // 5) Custom filtering logic
    $.fn.dataTable.ext.search.push(function(settings, data, dataIndex){
        var tableId = settings.nTable.id; // Get the active table ID
        var pass = true;

        $('.filter-group').each(function(){
            var columnName = $(this).data('column');
            var colIndex   = $('#' + tableId + ' thead th')
                                .filter(function(){ return $(this).text().trim() === columnName; })
                                .index();
            var fromVal    = $(this).find('.from').val();
            var toVal      = $(this).find('.to').val();
            var cellVal    = data[colIndex] || '';
            cellVal        = cellVal.replace(/<[^>]*>?/gm,''); // Remove HTML tags
            var num        = parseFloat(cellVal.replace(/[^0-9\.-]+/g,'')); // Parse as number
            
            if (!isNaN(num)) {
                if (fromVal && num < parseFloat(fromVal)) pass = false;
                if (toVal   && num > parseFloat(toVal))   pass = false;
            } else {
                if (fromVal && cellVal.toLowerCase() < fromVal) pass = false;
                if (toVal   && cellVal.toLowerCase() > toVal)   pass = false;
            }
        });

        return pass;
    });
});

// Tab‐switcher stays here too
function openTab(evt, tabName) {
    $('.tabcontent').hide();
    $('#' + tabName).show();
    $('.tab button').removeClass('active');
    $(evt.currentTarget).addClass('active');
}
</script>
    """
    html = f"""
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
      <meta charset=\"UTF-8\">
      <title>Crypto Data Table</title>
      {styles}
    </head>
    <body>
      <!-- Shared Filter Controls -->
      <div id=\"filterControls\">
          <input type=\"text\" id=\"nameFilter\" placeholder=\"Filter by coin name\">
          <button id=\"otherFiltersBtn\">Other filters</button>
      </div>
      <!-- Other Filters Popup -->
      <div id=\"otherFiltersPopup\">
          <h4>Other Filters</h4>
          <div id=\"otherFiltersContent\"></div>
          <div style=\"text-align: center; margin-top: 10px;\">
            <button id=\"applyOtherFilters\">Apply</button>
            <button id=\"closeOtherFilters\">Close</button>
          </div>
      </div>
      <!-- Tabs -->
      <div class=\"tab\">
        <button id="tab1Btn" class="active" onclick="openTab(event,'mainTab')">Coin Price</button>
        <button id="tab2Btn" onclick="openTab(event,'mcTab')">Market Cap</button>
      </div>
      <!-- Main Tab -->
      <div id=\"mainTab\" class=\"tabcontent\">
        <div class=\"crypto-table-container\">{main_html}</div>
      </div>
      <!-- Market Cap Tab -->
      <div id=\"mcTab\" class=\"tabcontent\">
        <div class=\"crypto-table-container\">{mc_html}</div>
      </div>
      <!-- Last Updated -->
      <div class=\"last-updated-container\"><p>Data last updated: {last_updated_str} UTC</p></div>
      {scripts}
    </body>
    </html>
    """
    return html


def generate_crypto_table_html():
    df = fetch_data_from_google_sheets()
    main_html = generate_html_table(df)
    mc_html   = generate_mc_table_html(df)
    last_updated = extract_last_updated_info(df)
    full_html = generate_html_page(main_html, mc_html, last_updated)
    with open("crypto_table.html", "w", encoding="utf-8") as f:
        f.write(full_html)
    print("HTML table generated with two tabs: crypto_table.html")


def main():
    try:
        generate_crypto_table_html()
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
