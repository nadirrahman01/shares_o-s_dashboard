import streamlit as st
import sqlite3
import requests
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

ALPHA_VANTAGE_API_KEY = 'HZ2YALVCOTH1H1HN'  # Your provided API key

# Function to fetch company overview data
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

# Function to fetch insider transactions
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

# Function to fetch corporate actions
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

# Function to update database
def update_database(ticker, isin, outstanding_shares, details, transactions, actions):
    conn = sqlite3.connect('shares_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO shares (ticker, isin, outstanding_shares, last_updated, details, transactions, actions)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (ticker, isin, outstanding_shares, datetime.now().date(), json.dumps(details), json.dumps(transactions), json.dumps(actions)))
    conn.commit()
    conn.close()

# Function to query database
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

# Streamlit layout
st.set_page_config(page_title="Outstanding Shares Dashboard", layout="wide")

st.title('📊 Outstanding Shares Dashboard')

ticker_or_isin = st.text_input('Enter Ticker or ISIN:', placeholder='e.g. AAPL or US0378331005')
if st.button('Search'):
    ticker_or_isin = ticker_or_isin.upper()  # Convert input to uppercase for case insensitivity
    with st.spinner('Fetching data...'):
        result = query_database(ticker_or_isin)
        if result:
            st.success('Data found in the database.')
            st.write(f"### {result[0]} - {result[1]}")
            st.write(f"**Outstanding Shares:** {result[2]:,}")
            st.write(f"**Last Updated:** {result[3]}")

            st.write("### Details")
            details = safe_json_loads(result[4]) if result[4] else {}
            for key, value in details.items():
                st.write(f"**{key}:** {value}")

            st.write("### Insider Transactions")
            transactions = safe_json_loads(result[5]) if result[5] else []
            if transactions:
                for transaction in transactions:
                    st.write(f"**{transaction['transactionDate']}:** {transaction['transactionType']} - {transaction['shares']} shares")
            else:
                st.write("No Insider Transactions found.")

            st.write("### Corporate Actions")
            actions = safe_json_loads(result[6]) if result[6] else []
            if actions:
                for action in actions:
                    st.write(f"**{action['reportDate']}:** {action['corporateAction']} - {action['description']}")
            else:
                st.write("No Corporate Actions found.")
        else:
            st.warning('No data found in the database. Fetching from Alpha Vantage...')
            if ticker_or_isin.isdigit():
                st.error("ISIN should not be numeric. Please enter a valid ticker or ISIN.")
            else:
                ticker = ticker_or_isin
                isin = ticker_or_isin  # You might need to map ticker to ISIN if required
                outstanding_shares, details = fetch_data_from_alpha_vantage(ticker)
                transactions = fetch_insider_transactions(ticker)
                actions = fetch_corporate_actions(ticker)
                if outstanding_shares:
                    update_database(ticker, isin, outstanding_shares, details, transactions, actions)
                    st.success('Data fetched and updated successfully.')
                    st.write(f"### {ticker} - {isin}")
                    st.write(f"**Outstanding Shares:** {outstanding_shares:,}")
                    st.write(f"**Last Updated:** {datetime.now().date()}")

                    st.write("### Details")
                    for key, value in details.items():
                        st.write(f"**{key}:** {value}")

                    st.write("### Insider Transactions")
                    if transactions:
                        for transaction in transactions:
                            st.write(f"**{transaction['transactionDate']}:** {transaction['transactionType']} - {transaction['shares']} shares")
                    else:
                        st.write("No Insider Transactions found.")

                    st.write("### Corporate Actions")
                    if actions:
                        for action in actions:
                            st.write(f"**{action['reportDate']}:** {action['corporateAction']} - {action['description']}")
                    else:
                        st.write("No Corporate Actions found.")
                else:
                    st.error('Failed to fetch outstanding shares data. Please check the input values and try again.')
                    if details:
                        st.write(f"API Response: {json.dumps(details, indent=2)}")
                    else:
                        st.write("No API response available.")