import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# Set up the Streamlit app
st.title('Multi-Exchange Fee Comparison')

# Sidebar for user inputs
st.sidebar.header('User Inputs')

# Time period selection
st.sidebar.subheader('Time Period Selection')
time_value = st.sidebar.number_input('Enter number of time units', min_value=1, value=7, step=1)
time_unit = st.sidebar.selectbox('Select time unit', ['Hours', 'Days', 'Months'])

# Calculate the start date based on the selected time period
end_date = datetime.now()
if time_unit == 'Hours':
    start_date = end_date - timedelta(hours=time_value)
elif time_unit == 'Days':
    start_date = end_date - timedelta(days=time_value)
else:  # Months
    start_date = end_date - timedelta(days=time_value * 30)  # Approximating a month to 30 days

# Format dates for API request
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = end_date.strftime('%Y-%m-%d')

# Asset selection
assets = ['SOL', 'ETH', 'BONK']
selected_asset = st.sidebar.selectbox('Select Asset', assets)

# Margin size input
margin_size = st.sidebar.number_input('Margin Size (USD)', min_value=1.0, value=10000.0, step=100.0)

# Leverage selection
leverage_options = [1.5, 2.0, 3.0, 4.0, 5.0]
selected_leverage = st.sidebar.selectbox('Select Leverage', leverage_options)

# Asgard Inputs
st.sidebar.subheader('Asgard Inputs')
asgard_borrow_assets = ['USDC', 'USDT']
asgard_borrow_asset = st.sidebar.selectbox('Select Asgard Borrow Asset', asgard_borrow_assets)

# Function to fetch data from the API
def fetch_data(start_date, end_date):
    url = f"http://159.223.14.10:6969/fee-comparisons?from={start_date}&to={end_date}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch data: {response.status_code}")
        return None

def calculate_fees(df, selected_asset, margin_size, leverage, asgard_borrow_asset):
    position_size = margin_size * leverage
    
    st.write(f"Calculating fees for asset: {selected_asset}")
    st.write(f"Position size: ${position_size:.2f}")
    
    # Drift calculations
    drift_open_close_fee = 0.001 * position_size
    drift_funding_rates = df['drift.SOLPerp.driftHourlyFunding'] # driftHourlyFunding is in percentage
    drift_total_funding_rate = drift_funding_rates.sum() / 100  # Convert percentage to decimal
    drift_variable_fees = drift_total_funding_rate * position_size
    drift_total_fees = (2 * drift_open_close_fee) + drift_variable_fees

    # Flash Trade calculations
    flash_open_close_fee = 0.0015 * position_size
    flash_swap_fee = 0.0007 * margin_size
    flash_borrow_rate_column = f'flashPerp.{selected_asset.lower()}Token.HourlyBorrowRate'
    if flash_borrow_rate_column in df.columns:
        flash_borrow_rates = df[flash_borrow_rate_column]
        flash_total_borrow_rate = flash_borrow_rates.sum() / 100  # Convert percentage to decimal
        flash_variable_fees = flash_total_borrow_rate * position_size
    else:
        st.warning(f"Could not find borrow rate data for {selected_asset} in Flash Trade. Using 0 for calculations.")
        flash_variable_fees = 0
        flash_borrow_rates = pd.Series([0] * len(df))
    flash_total_fees = (2 * flash_open_close_fee) + (2 * flash_swap_fee) + flash_variable_fees

    # Jup Perps calculations
    if selected_asset == 'SOL':
        jup_trading_fee_coefficient = 0.0005 + (position_size / 1_000_000_000)
    elif selected_asset == 'ETH':
        jup_trading_fee_coefficient = 0.0005 + (position_size / 5_000_000_000)
    else:
        jup_trading_fee_coefficient = 0.0005  # Default for other assets
    
    jup_open_fee = jup_trading_fee_coefficient * position_size
    jup_close_fee = 0.0007 * position_size
    jup_borrow_rate_column = f'jupPerp.{selected_asset.lower()}Token.HourlyBorrowRate' # HourlyBorrowRate is in percentage
    if jup_borrow_rate_column in df.columns:
        jup_borrow_rates = df[jup_borrow_rate_column]
        jup_total_borrow_rate = jup_borrow_rates.sum() / 100  # Convert percentage to decimal
        jup_variable_fees = jup_total_borrow_rate * position_size
    else:
        st.warning(f"Could not find borrow rate data for {selected_asset} in Jup Perps. Using 0 for calculations.")
        jup_variable_fees = 0
        jup_borrow_rates = pd.Series([0] * len(df))
    jup_total_fees = jup_open_fee + jup_close_fee + jup_variable_fees

    # Asgard (MarginFi) calculations
    asgard_open_close_fee = 0.0007 * position_size
    asgard_deposit_rate_column = f'marginfi.{selected_asset.lower()}Token.depositIRate' # depositIRate is in decimals
    asgard_borrow_rate_column = f'marginfi.{asgard_borrow_asset.lower()}Token.borrowIRate' # borrowIRate is in decimals
    if asgard_deposit_rate_column in df.columns and asgard_borrow_rate_column in df.columns:
        asgard_deposit_rates = df[asgard_deposit_rate_column] / (365 * 24) * 100  # Convert annual decimals to hourly percentage
        asgard_borrow_rates = df[asgard_borrow_rate_column] / (365 * 24) * 100 # Convert annual decimals to hourly percentage
        asgard_net_rates = asgard_borrow_rates - asgard_deposit_rates
        asgard_actual_net_rates = asgard_borrow_rates - (asgard_deposit_rates * leverage)
        asgard_total_actual_net_rate = asgard_actual_net_rates.sum() / 100  # Convert percentage to decimal
        asgard_variable_fees = asgard_total_actual_net_rate * margin_size
    else:
        st.warning(f"Could not find rate data for Asgard (MarginFi). Using 0 for calculations.")
        asgard_variable_fees = 0
        asgard_net_rates = pd.Series([0] * len(df))
        asgard_actual_net_rates = pd.Series([0] * len(df))
    asgard_total_fees = (2 * asgard_open_close_fee) + asgard_variable_fees

    # Create time series for variable fees and total fees
    timestamps = pd.to_datetime(df['createdAt'])
    drift_variable_fees_series = drift_funding_rates.cumsum() / 100 * position_size
    flash_variable_fees_series = flash_borrow_rates.cumsum() / 100 * position_size
    jup_variable_fees_series = jup_borrow_rates.cumsum() / 100 * position_size
    asgard_variable_fees_series = asgard_actual_net_rates.cumsum() / 100 * margin_size

    drift_total_fees_series = drift_variable_fees_series + (2 * drift_open_close_fee)
    flash_total_fees_series = flash_variable_fees_series + (2 * flash_open_close_fee) + (2 * flash_swap_fee)
    jup_total_fees_series = jup_variable_fees_series + jup_open_fee + jup_close_fee
    asgard_total_fees_series = asgard_variable_fees_series + (2 * asgard_open_close_fee)

    variable_fees_df = pd.DataFrame({
        'Timestamp': timestamps,
        'Drift': drift_variable_fees_series,
        'Flash Trade': flash_variable_fees_series,
        'Jup Perps': jup_variable_fees_series,
        'Asgard (MarginFi)': asgard_variable_fees_series
    })

    total_fees_df = pd.DataFrame({
        'Timestamp': timestamps,
        'Drift': drift_total_fees_series,
        'Flash Trade': flash_total_fees_series,
        'Jup Perps': jup_total_fees_series,
        'Asgard (MarginFi)': asgard_total_fees_series
    })

    return {
        'Exchange': ['Drift', 'Flash Trade', 'Jup Perps', 'Asgard (MarginFi)'],
        'Open Fees': [drift_open_close_fee, flash_open_close_fee + flash_swap_fee, jup_open_fee, asgard_open_close_fee],
        'Variable Fees': [drift_variable_fees, flash_variable_fees, jup_variable_fees, asgard_variable_fees],
        'Close Fees': [drift_open_close_fee, flash_open_close_fee + flash_swap_fee, jup_close_fee, asgard_open_close_fee],
        'Total Fees': [drift_total_fees, flash_total_fees, jup_total_fees, asgard_total_fees]
    }, asgard_net_rates, variable_fees_df, total_fees_df

# Display selected inputs in the main area
st.subheader('Selected Inputs')
st.write(f"Time Period: {time_value} {time_unit}")
st.write(f"Date Range: {start_date_str} to {end_date_str}")
st.write(f"Asset: {selected_asset}")
st.write(f"Margin Size: ${margin_size:.2f}")
st.write(f"Leverage: {selected_leverage}x")
st.write(f"Asgard Borrow Asset: {asgard_borrow_asset}")

# Fetch data when the user clicks the button
if st.sidebar.button('Calculate Fees'):
    data = fetch_data(start_date_str, end_date_str)
    
    if data:
        st.success("Data fetched successfully!")
        
        df = pd.json_normalize(data)
        fees, asgard_net_rates, variable_fees_df, total_fees_df = calculate_fees(df, selected_asset, margin_size, selected_leverage, asgard_borrow_asset)
        
        st.subheader("Fee Comparison")
        fee_df = pd.DataFrame(fees)
        st.table(fee_df.set_index('Exchange').style.format('${:.2f}'))

        st.subheader("Rate Statistics")
        drift_funding_rates = df['drift.SOLPerp.driftHourlyFunding']
        flash_borrow_rate_column = f'flashPerp.{selected_asset.lower()}Token.HourlyBorrowRate'
        jup_borrow_rate_column = f'jupPerp.{selected_asset.lower()}Token.HourlyBorrowRate'
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write("Drift Funding Rates")
            st.write(f"Average: {drift_funding_rates.mean():.4f}%")
            st.write(f"Total: {drift_funding_rates.sum():.4f}%")
            st.write(f"Cumulative Effect: {(drift_funding_rates.sum() / 100) * 100:.4f}%")
        
        with col2:
            st.write("Flash Trade Borrow Rates")
            if flash_borrow_rate_column in df.columns:
                flash_borrow_rates = df[flash_borrow_rate_column]
                st.write(f"Average: {flash_borrow_rates.mean():.4f}%")
                st.write(f"Total: {flash_borrow_rates.sum():.4f}%")
                st.write(f"Cumulative Effect: {flash_borrow_rates.sum():.4f}%")
            else:
                st.write("No data available")
        
        with col3:
            st.write("Jup Perps Borrow Rates")
            if jup_borrow_rate_column in df.columns:
                jup_borrow_rates = df[jup_borrow_rate_column]
                st.write(f"Average: {jup_borrow_rates.mean():.4f}%")
                st.write(f"Total: {jup_borrow_rates.sum():.4f}%")
                st.write(f"Cumulative Effect: {jup_borrow_rates.sum():.4f}%")
            else:
                st.write("No data available")
        
        with col4:
            st.write("Asgard (MarginFi) Net Rates")
            st.write(f"Average: {asgard_net_rates.mean():.4f}%")
            st.write(f"Total: {asgard_net_rates.sum():.4f}%")
            st.write(f"Cumulative Effect: {asgard_net_rates.sum():.4f}%")
        
        st.subheader("Rates Over Time")
        rates_df = pd.DataFrame({
            'Drift Funding Rate': drift_funding_rates,
            'Asgard Net Rate': asgard_net_rates
        })
        if flash_borrow_rate_column in df.columns:
            rates_df['Flash Trade Borrow Rate'] = df[flash_borrow_rate_column]
        if jup_borrow_rate_column in df.columns:
            rates_df['Jup Perps Borrow Rate'] = df[jup_borrow_rate_column]
        st.line_chart(rates_df)

        # New chart for Variable Fees
        st.subheader("Variable Fees Over Time")
        variable_fees_chart = variable_fees_df.set_index('Timestamp')
        st.line_chart(variable_fees_chart)

        # New chart for Total Fees
        st.subheader("Total Fees Over Time")
        total_fees_chart = total_fees_df.set_index('Timestamp')
        st.line_chart(total_fees_chart)

    else:
        st.error("Failed to fetch data. Please try again.")