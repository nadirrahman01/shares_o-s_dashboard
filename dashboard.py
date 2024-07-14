import streamlit as st
import sqlite3
import requests
import json
from datetime import datetime  # Corrected import statement
import logging
import pandas as pd
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

ALPHA_VANTAGE_API_KEY = 'HZ2YALVCOTH1H1HN'
MARKETAUX_API_KEY = 'pKlPW4SUe3gHQm9dd0Top365tOjHzgnhzEdWW6Yl'

# Database setup
def init_db():
    conn = sqlite3.connect('shares_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            username TEXT,
            action TEXT,
            details TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shares (
            ticker TEXT PRIMARY KEY,
            isin TEXT,
            outstanding_shares INTEGER,
            last_updated TEXT,
            details TEXT,
            transactions TEXT,
            actions TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Utility functions
def log_action(username, action, details):
    conn = sqlite3.connect('shares_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_logs (timestamp, username, action, details)
        VALUES (?, ?, ?, ?)
    ''', (datetime.now().isoformat(), username, action, details))
    conn.commit()
    conn.close()

def fetch_data_from_alpha_vantage(ticker):
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}'
    response = requests.get(url)
    logging.debug(f"Request URL: {url}")
    logging.debug(f"Response Status Code: {response.status_code}")
    logging.debug(f"Response Text: {response.text}")
    if response.status_code == 200:
        data = response.json()
        if 'SharesOutstanding' in data:
            return int(data['SharesOutstanding']), data
        else:
            logging.error(f"SharesOutstanding field not found in the response for ticker {ticker}: {data}")
            return None, data
    else:
        logging.error(f"Failed to fetch data for ticker {ticker}. HTTP Status code: {response.status_code}")
        return None, response.text

def fetch_insider_transactions(ticker):
    url = f'https://www.alphavantage.co/query?function=INSIDER_TRANSACTIONS&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}'
    response = requests.get(url)
    logging.debug(f"Insider Transactions URL: {url}")
    logging.debug(f"Response Status Code: {response.status_code}")
    logging.debug(f"Response Text: {response.text}")
    if response.status_code == 200:
        data = response.json()
        return data.get('transactions', [])
    else:
        logging.error(f"Failed to fetch insider transactions for ticker {ticker}. HTTP Status code: {response.status_code}")
        return []

def fetch_corporate_actions(ticker):
    url = f'https://www.alphavantage.co/query?function=CORPORATE_ACTIONS&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}'
    response = requests.get(url)
    logging.debug(f"Corporate Actions URL: {url}")
    logging.debug(f"Response Status Code: {response.status_code}")
    logging.debug(f"Response Text: {response.text}")
    if response.status_code == 200:
        data = response.json()
        return data.get('actions', [])
    else:
        logging.error(f"Failed to fetch corporate actions for ticker {ticker}. HTTP Status code: {response.status_code}")
        return []

def update_database(ticker, isin, outstanding_shares, details, transactions, actions):
    conn = sqlite3.connect('shares_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO shares (ticker, isin, outstanding_shares, last_updated, details, transactions, actions)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (ticker, isin, outstanding_shares, datetime.now().date(), json.dumps(details), json.dumps(transactions), json.dumps(actions)))
    conn.commit()
    conn.close()
    log_action('user', 'Update Database', f'Ticker: {ticker}, ISIN: {isin}, Shares Outstanding: {outstanding_shares}')

def query_database(ticker_or_isin):
    conn = sqlite3.connect('shares_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ticker, isin, outstanding_shares, last_updated, details, transactions, actions
        FROM shares
        WHERE UPPER(ticker) = ? OR UPPER(isin) = ?
    ''', (ticker_or_isin, ticker_or_isin))
    result = cursor.fetchone()
    conn.close()
    return result

def safe_json_loads(json_string):
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return {}

def fetch_news(ticker):
    url = f'https://api.marketaux.com/v1/news/all?symbols={ticker}&filter_entities=true&language=en&api_token={MARKETAUX_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('data', [])
    else:
        logging.error(f"Failed to fetch news for ticker {ticker}. HTTP Status code: {response.status_code}")
        return []

# Streamlit layout
st.set_page_config(page_title="Outstanding Shares Dashboard", layout="wide")

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "Welcome"

# Navigation
st.sidebar.title("Navigation")
if st.sidebar.button('Welcome'):
    st.session_state.page = "Welcome"
if st.sidebar.button('Dashboard'):
    st.session_state.page = "Dashboard"
if st.sidebar.button('Audit Logs'):
    st.session_state.page = "Audit Logs"
if st.sidebar.button('News'):
    st.session_state.page = "News"

page = st.session_state.page

if page == "Welcome":
    st.title('Welcome to the Outstanding Shares Dashboard')
    st.write("""
    This dashboard allows you to search for stock tickers or ISINs and retrieve information about outstanding shares, insider transactions, corporate actions, and the latest financial news.
    You can also download the results as a PDF report.
    """)
    st.markdown(
        """
        <style>
        .button-container {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 10px;
        }
        .button-container a, .button-container .stButton {
            margin-bottom: 10px;
        }
        .button-container button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        .button-container .dashboard {
            background-color: #228B22;
        }
        .button-container button:hover {
            background-color: #45a049;
        }
        </style>
        <div class="button-container">
            <a href="https://eelslap.com/" target="_blank"><button>Developed by Nadir Rahman</button></a>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button('Enter the Dashboard'):
        st.session_state.page = "Dashboard"
        st.experimental_rerun()

elif page == "Dashboard":
    st.title('📊 Outstanding Shares Dashboard')

    ticker_or_isin = st.text_input('Enter Ticker or ISIN:', placeholder='e.g. AAPL or US0378331005')
    if st.button('Search'):
        ticker_or_isin = ticker_or_isin.upper()
        progress_bar = st.progress(0)
        for percent_complete in range(100):
            time.sleep(0.01)
            progress_bar.progress(percent_complete + 1)
        with st.spinner('Fetching data...'):
            result = query_database(ticker_or_isin)
            progress_bar.progress(0)  # Reset progress bar to 0 to hide it
            if result:
                st.success('Data found in the database.')
                st.write(f"### {result[0]} - {result[1]}")

                st.markdown(f"""
                <div style='display: flex;'>
                    <div style='background-color:#228B22; color:white; padding: 10px; border-radius: 5px; margin-right: 10px;'>
                        Shares Outstanding: {result[2]:,}
                    </div>
                    <div style='background-color:#32CD32; color:white; padding: 10px; border-radius: 5px;'>
                        Last Updated: {result[3]}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.write("### Details")
                details = safe_json_loads(result[4]) if result[4] else {}
                details_df = pd.DataFrame(details.items(), columns=['Key', 'Value'])
                with st.container():
                    st.dataframe(details_df, width=1500)

                st.write("### Insider Transactions")
                transactions = safe_json_loads(result[5]) if result[5] else []
                if transactions:
                    transactions_df = pd.DataFrame(transactions)
                    with st.container():
                        st.dataframe(transactions_df, width=1500)
                else:
                    st.write("No Insider Transactions found.")

                st.write("### Corporate Actions")
                actions = safe_json_loads(result[6]) if result[6] else []
                if actions:
                    actions_df = pd.DataFrame(actions)
                    with st.container():
                        st.dataframe(actions_df, width=1500)
                else:
                    st.write("No Corporate Actions found.")
                # Log the search action including the number of shares outstanding
                log_action('user', 'Search Ticker', f'Ticker: {result[0]}, ISIN: {result[1]}, Shares Outstanding: {result[2]}')
            else:
                st.warning('Data not found in the database. Fetching from API...')
                ticker, isin = (ticker_or_isin, None) if ticker_or_isin.isalpha() else (None, ticker_or_isin)
                outstanding_shares, details = fetch_data_from_alpha_vantage(ticker) if ticker else (None, None)
                transactions = fetch_insider_transactions(ticker) if ticker else []
                actions = fetch_corporate_actions(ticker) if ticker else []
                if outstanding_shares:
                    update_database(ticker, isin, outstanding_shares, details, transactions, actions)
                    st.success('Data fetched and updated successfully.')
                    st.write(f"### {ticker} - {isin}")

                    st.markdown(f"""
                    <div style='display: flex;'>
                        <div style='background-color:#228B22; color:white; padding: 10px; border-radius: 5px; margin-right: 10px;'>
                            Shares Outstanding: {outstanding_shares:,}
                        </div>
                        <div style='background-color:#32CD32; color:white; padding: 10px; border-radius: 5px;'>
                            Last Updated: {datetime.now().date()}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.write("### Details")
                    details_df = pd.DataFrame(details.items(), columns=['Key', 'Value'])
                    with st.container():
                        st.dataframe(details_df, width=1500)

                    st.write("### Insider Transactions")
                    if transactions:
                        transactions_df = pd.DataFrame(transactions)
                        with st.container():
                            st.dataframe(transactions_df, width=1500)
                    else:
                        st.write("No insider transactions found.")

                    st.write("### Corporate Actions")
                    if actions:
                        actions_df = pd.DataFrame(actions)
                        with st.container():
                            st.dataframe(actions_df, width=1500)
                    else:
                        st.write("No corporate actions found.")
                    # Log the search action including the number of shares outstanding
                    log_action('user', 'Search Ticker', f'Ticker: {ticker}, ISIN: {isin}, Shares Outstanding: {outstanding_shares}')
                else:
                    st.error('Failed to fetch data. Please check the input values and try again.')

elif page == "Audit Logs":
    st.title('🔍 Audit Logs')
    
    def fetch_audit_logs():
        conn = sqlite3.connect('shares_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM audit_logs')
        logs = cursor.fetchall()
        conn.close()
        return logs

    logs = fetch_audit_logs()

    if logs:
        logs_df = pd.DataFrame(logs, columns=['ID', 'Timestamp', 'Username', 'Action', 'Details'])
        st.dataframe(logs_df)
    else:
        st.write("No audit logs found.")

elif page == "News":
    st.title('📰 News and Updates')
    
    ticker = st.text_input('Enter Ticker:', placeholder='e.g. AAPL')
    if st.button('Fetch News'):
        if ticker:
            with st.spinner('Fetching news...'):
                articles = fetch_news(ticker)
                if articles:
                    for article in articles:
                        st.write(f"### {article['title']}")
                        st.write(f"{article['description']}")
                        st.write(f"*Published at: {article['published_at']}*")
                        st.write(f"[Read more]({article['url']})")
                        st.write("---")
                else:
                    st.write("No news articles found.")
        else:
            st.write("Please enter a ticker symbol.")
