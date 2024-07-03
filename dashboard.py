import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# Constants
ASSETS = ['SOL', 'ETH', 'BONK']
LEVERAGE_OPTIONS = [1.5, 2.0, 3.0, 4.0, 5.0]
ASGARD_BORROW_ASSETS = ['USDC', 'USDT']
API_URL = "http://159.223.14.10:6969/fee-comparisons"

def fetch_data(start_date, end_date):
    """Fetch data from API."""
    response = requests.get(f"{API_URL}?from={start_date}&to={end_date}")
    if response.status_code == 200:
        return response.json()
    st.error(f"Failed to fetch data: {response.status_code}")
    return None

def calculate_exchange_fees(df, exchange, asset, position_size, leverage, asgard_borrow_asset):
    """Calculate fees for a specific exchange."""
    open_fee = close_fee = variable_fees = total_fees = 0
    rates = pd.Series([0] * len(df))
    data_available = True

    if exchange == 'drift':
        funding_column = f'drift.{asset}Perp.driftHourlyFunding'
        if funding_column in df.columns:
            rates = df[funding_column]
            open_fee = 0.001 * position_size
            close_fee = open_fee
            variable_fees = rates.sum() / 100 * position_size
            total_fees = open_fee + close_fee + variable_fees
        else:
            data_available = False
            st.warning(f"Could not find funding rate data for {asset} in Drift. Using 0 for calculations.")
    elif exchange == 'flash':
        borrow_column = f'flashPerp.{asset.lower()}Token.HourlyBorrowRate'
        if borrow_column in df.columns:
            rates = df[borrow_column]
            open_fee = (0.0015 if asset == 'BONK' else 0.0008) * position_size
            close_fee = open_fee
            variable_fees = rates.sum() / 100 * position_size
            total_fees = open_fee + close_fee + variable_fees
        else:
            data_available = False
            st.warning(f"Could not find borrow rate data for {asset} in Flash Trade. Using 0 for calculations.")
    elif exchange == 'jup':
        borrow_column = f'jupPerp.{asset.lower()}Token.HourlyBorrowRate'
        if borrow_column in df.columns:
            rates = df[borrow_column]
            open_fee = (0.0007 + (position_size / (1e9 if asset == 'SOL' else 5e9))) * position_size
            close_fee = (0.0007 + (position_size / (1e9 if asset == 'SOL' else 5e9))) * position_size
            variable_fees = rates.sum() / 100 * position_size
            total_fees = open_fee + close_fee + variable_fees
        else:
            data_available = False
            st.warning(f"Could not find borrow rate data for {asset} in Jup Perps. Using 0 for calculations.")
    elif exchange in ['marginfi', 'kamino']:  # Asgard (MarginFi or Kamino)
        deposit_column = f'{exchange}.{asset.lower()}Token.depositIRate'
        borrow_column = f'{exchange}.{asgard_borrow_asset.lower()}Token.borrowIRate'
        if deposit_column in df.columns and borrow_column in df.columns:
            deposit_rates = df[deposit_column] / (365 * 24) * 100
            borrow_rates = df[borrow_column] / (365 * 24) * 100
            rates = borrow_rates - (borrow_rates / leverage) - deposit_rates
            open_fee = 0.0007 * position_size
            close_fee = open_fee
            variable_fees = rates.sum() / 100 * position_size
            total_fees = open_fee + close_fee + variable_fees
        else:
            data_available = False
            st.warning(f"Could not find rate data for Asgard ({exchange.capitalize()}). Using 0 for calculations.")
    
    return open_fee, variable_fees, close_fee, total_fees, rates, data_available

# Streamlit UI setup
st.title('Multi-Exchange Fee Comparison')

# Sidebar inputs
with st.sidebar:
    st.header('User Inputs')
    time_value = st.number_input('Enter number of time units', min_value=1, value=7, step=1)
    time_unit = st.selectbox('Select time unit', ['Hours', 'Days', 'Months'], index=1)
    SELECTED_ASSET = st.selectbox('Select Asset', ASSETS)
    INITIAL_CAPITAL = st.number_input('Initial Capital (USD)', min_value=1.0, value=10000.0, step=100.0)
    LEVERAGE = st.selectbox('Select Leverage', LEVERAGE_OPTIONS, index=1)
    ASGARD_BORROW_ASSET = st.selectbox('Select Asgard Borrow Asset', ASGARD_BORROW_ASSETS)

# Calculate date range
end_date = datetime.now()
start_date = end_date - timedelta(**{time_unit.lower(): time_value})
start_date_str, end_date_str = start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

# Display selected inputs
st.subheader('Selected Inputs')
st.write(f"Time Period: {time_value} {time_unit}")
st.write(f"Date Range: {start_date_str} to {end_date_str}")
st.write(f"Asset: {SELECTED_ASSET}")
st.write(f"Initial Capital: ${INITIAL_CAPITAL:.2f}")
st.write(f"Leverage: {LEVERAGE}x")
st.write(f"Asgard Borrow Asset: {ASGARD_BORROW_ASSET}")

# Calculate fees when button is clicked
if st.sidebar.button('Calculate Fees'):
    data = fetch_data(start_date_str, end_date_str)
    if data:
        st.success("Data fetched successfully!")
        df = pd.json_normalize(data)
        position_size = INITIAL_CAPITAL * LEVERAGE
        
        exchanges = ['drift', 'flash', 'jup', 'marginfi', 'kamino']
        exchange_names = {'drift': 'Drift', 'flash': 'Flash Trade', 'jup': 'Jup Perps', 
                          'marginfi': 'Asgard (MarginFi)', 'kamino': 'Asgard (Kamino)'}
        fees_data = {ex: calculate_exchange_fees(df, ex, SELECTED_ASSET, position_size, LEVERAGE, ASGARD_BORROW_ASSET) for ex in exchanges}
        
        # Create and display fee comparison table
        fee_df = pd.DataFrame({
            'Exchange': [exchange_names[ex] for ex in exchanges],
            'Open Fees': [fees_data[ex][0] for ex in exchanges],
            'Variable Fees': [fees_data[ex][1] for ex in exchanges],
            'Close Fees': [fees_data[ex][2] for ex in exchanges],
            'Total Fees': [fees_data[ex][3] for ex in exchanges]
        })
        st.subheader("Fee Comparison")
        st.table(fee_df.set_index('Exchange').style.format('${:.2f}'))
        
        # Display rate statistics
        st.subheader("Rate Statistics")
        cols = st.columns(len(exchanges))
        for i, ex in enumerate(exchanges):
            with cols[i]:
                st.write(f"{exchange_names[ex]} Rates")
                rates = fees_data[ex][4]
                if fees_data[ex][5]:  # Check if data is available
                    st.write(f"Average: {rates.mean():.4f}%")
                    st.write(f"Total: {rates.sum():.4f}%")
                    st.write(f"Cumulative Effect: {(rates.sum() / 100) * 100:.4f}%")
                else:
                    st.write("No data available")
        
        # Create and display charts
        st.subheader("Rates Over Time")
        rates_df = pd.DataFrame({exchange_names[ex]: fees_data[ex][4] for ex in exchanges if fees_data[ex][5]})
        if not rates_df.empty:
            st.line_chart(rates_df)
        else:
            st.write("No data available for rates over time")
        
        st.subheader("Variable Fees Over Time")
        variable_fees_df = pd.DataFrame({exchange_names[ex]: fees_data[ex][4].cumsum() / 100 * position_size for ex in exchanges if fees_data[ex][5]})
        if not variable_fees_df.empty:
            variable_fees_df.index = pd.to_datetime(df['createdAt'])
            st.line_chart(variable_fees_df)
        else:
            st.write("No data available for variable fees over time")
        
        st.subheader("Total Fees Over Time")
        total_fees_df = pd.DataFrame(index=pd.to_datetime(df['createdAt']))

        for ex in exchanges:
            if fees_data[ex][5]:  # If data is available
                open_fee, variable_fees, close_fee, _, rates, _ = fees_data[ex]
                
                # Start with open fee
                fees_series = pd.Series(open_fee, index=total_fees_df.index)
                
                # Add variable fees cumulatively
                cumulative_variable_fees = (rates.cumsum() / 100 * position_size).values
                fees_series += cumulative_variable_fees
                
                # Add close fee at the end
                fees_series.iloc[-1] += close_fee
                
                total_fees_df[exchange_names[ex]] = fees_series

        if not total_fees_df.empty:
            st.line_chart(total_fees_df)
        else:
            st.write("No data available for total fees over time")