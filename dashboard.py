import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

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

def calculate_exchange_fees(df, exchange, asset, position_size, leverage, asgard_borrow_asset, asgard_open_fee, asgard_close_fee):
    """Calculate fees for a specific exchange."""
    open_fee = close_fee = variable_fees = total_fees = 0
    rates = pd.Series([0] * len(df))
    data_available = True
    discount = None

    if exchange == 'drift':
        funding_column = f'drift.{asset}Perp.driftHourlyFunding'
        if funding_column in df.columns:
            rates = df[funding_column]
            base_fee_rate = 0.001
            
            if asset in ['SOL', 'ETH', 'BTC']:
                discounted_fee_rate = base_fee_rate * 0.25  # 75% discount
                open_fee = discounted_fee_rate * position_size
                close_fee = open_fee
                discount = '75%'
            else:
                open_fee = base_fee_rate * position_size
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
            open_fee = asgard_open_fee * position_size
            close_fee = asgard_close_fee * position_size
            variable_fees = rates.sum() / 100 * position_size
            total_fees = open_fee + close_fee + variable_fees
        else:
            data_available = False
            st.warning(f"Could not find rate data for Asgard ({exchange.capitalize()}). Using 0 for calculations.")
    
    return open_fee, variable_fees, close_fee, total_fees, rates, data_available, discount

def debug_asgard_calculations(exchange, asset, asgard_borrow_asset, df, position_size, leverage, asgard_open_fee, asgard_close_fee):
    st.subheader(f"Debug: Asgard ({exchange.capitalize()}) Calculations")
    
    deposit_column = f'{exchange}.{asset.lower()}Token.depositIRate'
    borrow_column = f'{exchange}.{asgard_borrow_asset.lower()}Token.borrowIRate'
    
    st.write(f"Asset: {asset}")
    st.write(f"Borrow Asset: {asgard_borrow_asset}")
    st.write(f"Position Size: ${position_size:.2f}")
    st.write(f"Leverage: {leverage}x")
    st.write(f"Opening Fee: {asgard_open_fee*100:.2f}%")
    st.write(f"Closing Fee: {asgard_close_fee*100:.2f}%")
    
    if deposit_column in df.columns and borrow_column in df.columns:
        yearly_deposit_rates = df[deposit_column] * 100  # Convert to percentage
        yearly_borrow_rates = df[borrow_column] * 100  # Convert to percentage
        deposit_rates = df[deposit_column] / (365 * 24) * 100
        borrow_rates = df[borrow_column] / (365 * 24) * 100
        net_rates = borrow_rates - (borrow_rates / leverage) - deposit_rates
        hourly_fees = net_rates / 100 * position_size
        
        st.write("Rates and Fees:")
        debug_df = pd.DataFrame({
            'Timestamp': df['createdAt'],
            'Yearly Deposit Rate (%)': yearly_deposit_rates,
            'Yearly Borrow Rate (%)': yearly_borrow_rates,
            'Hourly Deposit Rate (%)': deposit_rates,
            'Hourly Borrow Rate (%)': borrow_rates,
            'Hourly Net Rate (%)': net_rates,
            'Hourly Fees ($)': hourly_fees
        })
        st.dataframe(debug_df.style.format({
            'Yearly Deposit Rate (%)': '{:.6f}',
            'Yearly Borrow Rate (%)': '{:.6f}',
            'Hourly Deposit Rate (%)': '{:.6f}',
            'Hourly Borrow Rate (%)': '{:.6f}',
            'Hourly Net Rate (%)': '{:.6f}',
            'Hourly Fees ($)': '{:.6f}'
        }))
        
        st.write(f"Average Yearly Deposit Rate: {yearly_deposit_rates.mean():.6f}%")
        st.write(f"Average Yearly Borrow Rate: {yearly_borrow_rates.mean():.6f}%")
        st.write(f"Average Hourly Deposit Rate: {deposit_rates.mean():.6f}%")
        st.write(f"Average Hourly Borrow Rate: {borrow_rates.mean():.6f}%")
        st.write(f"Average Hourly Net Rate: {net_rates.mean():.6f}%")
        st.write(f"Average Hourly Fees: ${hourly_fees.mean():.6f}")
        
        open_fee = asgard_open_fee * position_size
        close_fee = asgard_close_fee * position_size
        variable_fees = hourly_fees.sum()
        total_fees = open_fee + close_fee + variable_fees
        
        st.write(f"Open Fee: ${open_fee:.6f}")
        st.write(f"Close Fee: ${close_fee:.6f}")
        st.write(f"Total Variable Fees: ${variable_fees:.6f}")
        st.write(f"Total Fees: ${total_fees:.6f}")
        
        st.subheader("Rates Over Time")
        rates_chart_df = debug_df.set_index('Timestamp')[['Hourly Deposit Rate (%)', 'Hourly Borrow Rate (%)', 'Hourly Net Rate (%)']]
        st.line_chart(rates_chart_df)
        
        st.subheader("Hourly Fees Over Time")
        st.line_chart(debug_df.set_index('Timestamp')[['Hourly Fees ($)']])
    else:
        st.write("Required data not found in the dataframe.")

def debug_drift_calculations(df, asset, position_size):
    st.subheader(f"Debug: Drift Calculations for {asset}")
    
    funding_column = f'drift.{asset}Perp.driftHourlyFunding'
    
    st.write(f"Asset: {asset}")
    st.write(f"Position Size: ${position_size:.2f}")
    
    if funding_column in df.columns:
        funding_rates = df[funding_column]
        hourly_fees = funding_rates / 100 * position_size
        
        st.write("Funding Rates and Fees:")
        debug_df = pd.DataFrame({
            'Timestamp': df['createdAt'],
            'Hourly Funding Rate (%)': funding_rates,
            'Hourly Fees ($)': hourly_fees
        })
        st.dataframe(debug_df.style.format({
            'Hourly Funding Rate (%)': '{:.6f}',
            'Hourly Fees ($)': '{:.6f}'
        }))
        
        st.write(f"Average Hourly Funding Rate: {funding_rates.mean():.6f}%")
        st.write(f"Average Hourly Fees: ${hourly_fees.mean():.6f}")
        
        base_fee_rate = 0.001  # 0.1%
        if asset in ['SOL', 'ETH', 'BTC']:
            fee_rate = base_fee_rate * 0.25  # 75% discount
            st.write(f"Fee Rate (75% discounted): {fee_rate:.4f} ({fee_rate*100:.2f}%)")
        else:
            fee_rate = base_fee_rate
            st.write(f"Fee Rate: {fee_rate:.4f} ({fee_rate*100:.2f}%)")
        
        open_fee = fee_rate * position_size
        close_fee = open_fee
        variable_fees = hourly_fees.sum()
        total_fees = open_fee + close_fee + variable_fees
        
        st.write(f"Open Fee: ${open_fee:.6f}")
        st.write(f"Close Fee: ${close_fee:.6f}")
        st.write(f"Total Variable Fees: ${variable_fees:.6f}")
        st.write(f"Total Fees: ${total_fees:.6f}")
        
        st.subheader("Funding Rates Over Time")
        st.line_chart(debug_df.set_index('Timestamp')[['Hourly Funding Rate (%)']])
        
        st.subheader("Hourly Fees Over Time")
        st.line_chart(debug_df.set_index('Timestamp')[['Hourly Fees ($)']])
    else:
        st.write(f"Required data not found in the dataframe for {asset} on Drift.")

def calculate_hourly_variable_fees(df, exchange, asset, position_size, leverage, asgard_borrow_asset):
    if exchange == 'drift':
        funding_column = f'drift.{asset}Perp.driftHourlyFunding'
        if funding_column in df.columns:
            return df[funding_column] / 100 * position_size
    elif exchange == 'flash':
        borrow_column = f'flashPerp.{asset.lower()}Token.HourlyBorrowRate'
        if borrow_column in df.columns:
            return df[borrow_column] / 100 * position_size
    elif exchange == 'jup':
        borrow_column = f'jupPerp.{asset.lower()}Token.HourlyBorrowRate'
        if borrow_column in df.columns:
            return df[borrow_column] / 100 * position_size
    elif exchange in ['marginfi', 'kamino']:
        deposit_column = f'{exchange}.{asset.lower()}Token.depositIRate'
        borrow_column = f'{exchange}.{asgard_borrow_asset.lower()}Token.borrowIRate'
        if deposit_column in df.columns and borrow_column in df.columns:
            deposit_rates = df[deposit_column] / (365 * 24) * 100
            borrow_rates = df[borrow_column] / (365 * 24) * 100
            net_rates = borrow_rates - (borrow_rates / leverage) - deposit_rates
            return net_rates / 100 * position_size
    return pd.Series([0] * len(df))  # Return a series of zeros if data is not available

# Streamlit UI setup
st.title('Multi-Exchange Fee Comparison')

# Sidebar inputs
with st.sidebar:
    st.header('User Inputs')
    time_value = st.number_input('Enter number of time units', min_value=1, value=1, step=1)
    time_unit = st.selectbox('Select time unit', ['Hours', 'Days', 'Months'], index=2)
    SELECTED_ASSET = st.selectbox('Select Asset', ASSETS, index=2)
    INITIAL_CAPITAL = st.number_input('Initial Capital (USD)', min_value=1.0, value=10000.0, step=100.0)
    LEVERAGE = st.selectbox('Select Leverage', LEVERAGE_OPTIONS, index=1)
    ASGARD_BORROW_ASSET = st.selectbox('Select Asgard Borrow Asset', ASGARD_BORROW_ASSETS)
    
    # New inputs for Asgard fees
    st.subheader('Asgard Fees')
    ASGARD_OPEN_FEE = st.number_input('Asgard Opening Fee (%)', min_value=0.0, max_value=100.0, value=0.06, step=0.01, format="%.2f") / 100
    ASGARD_CLOSE_FEE = st.number_input('Asgard Closing Fee (%)', min_value=0.0, max_value=100.0, value=0.06, step=0.01, format="%.2f") / 100

# Calculate date range
end_date = datetime.now()
if time_unit == 'Months':
    start_date = end_date - relativedelta(months=time_value)
else:
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
st.write(f"Asgard Opening Fee: {ASGARD_OPEN_FEE*100:.2f}%")
st.write(f"Asgard Closing Fee: {ASGARD_CLOSE_FEE*100:.2f}%")

# Automatically calculate fees
data = fetch_data(start_date_str, end_date_str)
if data:
    st.success("Data fetched successfully!")
    df = pd.json_normalize(data)
    position_size = INITIAL_CAPITAL * LEVERAGE
    
    exchanges = ['drift', 'flash', 'jup', 'marginfi', 'kamino']
    exchange_names = {'drift': 'Drift', 'flash': 'Flash Trade', 'jup': 'Jup Perps', 
                      'marginfi': 'Asgard (MarginFi)', 'kamino': 'Asgard (Kamino)'}
    fees_data = {ex: calculate_exchange_fees(df, ex, SELECTED_ASSET, position_size, LEVERAGE, ASGARD_BORROW_ASSET, ASGARD_OPEN_FEE, ASGARD_CLOSE_FEE) for ex in exchanges}
    
    # Create and display fee comparison table
    fee_df = pd.DataFrame({
        'Exchange': [exchange_names[ex] for ex in exchanges],
        'Discount': ['None' if fees_data[ex][6] is None else fees_data[ex][6] for ex in exchanges],
        'Open Fees': [fees_data[ex][0] for ex in exchanges],
        'Variable Fees': [fees_data[ex][1] for ex in exchanges],
        'Close Fees': [fees_data[ex][2] for ex in exchanges],
        'Total Fees': [fees_data[ex][3] for ex in exchanges]
    })
    fee_df = fee_df[['Exchange', 'Discount', 'Open Fees', 'Variable Fees', 'Close Fees', 'Total Fees']]
    
    st.subheader("Fee Comparison")
    st.table(fee_df.set_index('Exchange').style.format({
        'Open Fees': '${:.2f}',
        'Variable Fees': '${:.2f}',
        'Close Fees': '${:.2f}',
        'Total Fees': '${:.2f}',
        'Discount': '{}'
    }))
    
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
    
    # Create hourly variable fees chart for all exchanges
    st.subheader("Hourly Variable Fees Comparison")
    hourly_fees_df = pd.DataFrame({
        exchange_names[ex]: calculate_hourly_variable_fees(df, ex, SELECTED_ASSET, position_size, LEVERAGE, ASGARD_BORROW_ASSET)
        for ex in exchanges
    })
    hourly_fees_df.index = pd.to_datetime(df['createdAt'])
    
    # Display statistics
    st.write("Average Hourly Variable Fees:")
    for ex in exchanges:
        avg_fee = hourly_fees_df[exchange_names[ex]].mean()
        st.write(f"{exchange_names[ex]}: ${avg_fee:.6f}")
    
    # Create and display the chart
    st.line_chart(hourly_fees_df)

    # Create and display cumulative variable fees chart
    st.subheader("Cumulative Variable Fees Comparison")
    cumulative_fees_df = hourly_fees_df.cumsum()
    st.line_chart(cumulative_fees_df)
    
    st.subheader("Total Fees Over Time")
    total_fees_df = pd.DataFrame(index=pd.to_datetime(df['createdAt']))

    for ex in exchanges:
        if fees_data[ex][5]:  # If data is available
            open_fee, variable_fees, close_fee, _, rates, _ = fees_data[ex][:6]
            
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

    # Debug Drift calculations
    if fees_data['drift'][5]:  # If data is available for Drift
        debug_drift_calculations(df, SELECTED_ASSET, position_size)
    
    # Debug Asgard calculations
    for ex in ['marginfi', 'kamino']:
        if fees_data[ex][5]:  # If data is available
            debug_asgard_calculations(ex, SELECTED_ASSET, ASGARD_BORROW_ASSET, df, position_size, LEVERAGE, ASGARD_OPEN_FEE, ASGARD_CLOSE_FEE)