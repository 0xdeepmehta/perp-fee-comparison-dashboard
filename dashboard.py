import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Set up the Streamlit app
st.title('Fee Comparisons Dashboard')

# Sidebar for user inputs
st.sidebar.header('User Inputs')

# Date range selection in the sidebar
st.sidebar.subheader('Date Range Selection')
start_date = st.sidebar.date_input('Start Date', datetime.now() - timedelta(days=7))
end_date = st.sidebar.date_input('End Date', datetime.now())

# Asset selection
assets = ['SOL', 'ETH', 'USDC', 'USDT', 'BONK']  # Add more assets as needed
selected_asset = st.sidebar.selectbox('Select Asset', assets)

# Margin size input
margin_size = st.sidebar.number_input('Margin Size (USD)', min_value=1.0, value=1000.0, step=100.0)

# Leverage selection
leverage_options = [1.5, 2.0, 3.0, 4.0, 5.0]
selected_leverage = st.sidebar.selectbox('Select Leverage', leverage_options)

# Function to fetch data from the API
def fetch_data(start_date, end_date):
    url = f"http://159.223.14.10:6969/fee-comparisons?from={start_date}&to={end_date}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch data: {response.status_code}")
        return None

# Fetch data when the user clicks the button
if st.sidebar.button('Fetch Data'):
    data = fetch_data(start_date, end_date)
    
    if data:
        st.success("Data fetched successfully!")
        
        # Convert data to DataFrame
        df = pd.json_normalize(data)
        
        # Display raw data
        st.subheader("Raw Data")
        st.write(df)
        
        # TODO: Add calculations and chart plotting here
        
        # For now, we'll just print the columns to see what data we have
        st.subheader("Available Columns")
        st.write(df.columns)

# Display selected inputs in the main area
st.subheader('Selected Inputs')
st.write(f"Date Range: {start_date} to {end_date}")
st.write(f"Asset: {selected_asset}")
st.write(f"Margin Size: ${margin_size:.2f}")
st.write(f"Leverage: {selected_leverage}x")

# Add more Streamlit components and data processing logic here