import streamlit as st
import requests
import json

st.title("Comparison Meta Data")

# Fetch data from the endpoint
url = "https://perp-fee-comparison.0xdeepmehta.workers.dev/"
response = requests.get(url)
data = response.json()

# Extract data
marginfi = data['marginfi']
jupPerp = data['jupPerp']
flashPerp = data['flashPerp']

# Display basic info
st.header("Basic Information")
st.write(f"""
### Marginfi
- Deposit Token I Rate: {(marginfi['depositTokenIRate'] * 100):.2f}%
- Borrow Token I Rate: {(marginfi['borrowTokenIRate'] * 100):.2f}%
- Annualized Borrow Rate: {abs(marginfi['netApy'] * 100):.2f}%

### JUP PERP
- Current LTV: {jupPerp['jupCurrentLTV']} SOL
- Current Borrowed: {jupPerp['jupCurrentBorrowed']} SOL
- Current Utilization: {jupPerp['jupCurrentUtilization']}%
- Annualized Borrow Rate: {jupPerp['jupAnnualRate']:.2f}%

### FLASH PERP
- Current LTV: {flashPerp['flashCurrentLTV']} SOL
- Current Borrowed: {flashPerp['flashCurrentBorrowed']} SOL
- Current Utilization: {flashPerp['flashCurrentUtilization']}%
- Annualized Borrow Rate: {flashPerp['flashAnnualRate']:.2f}%
""")

# Input for SOL price in USD
sol_price_usd = st.number_input("Enter current SOL price in USD", min_value=0.01, value=50.0, step=0.01)
st.write(f"Current SOL price: ${sol_price_usd:.2f}")

# Slider for initial margin in USD
initial_margin_usd = st.slider("Initial Margin (USD)", min_value=1.0, max_value=5000.0, value=100.0, step=1.0)
st.write(f"Initial Margin: ${initial_margin_usd:.2f}")

# Convert initial margin to SOL
initial_margin_sol = initial_margin_usd / sol_price_usd
st.write(f"Initial Margin in SOL: {initial_margin_sol:.6f} SOL")

# Leverage levels
leverage_levels = [2, 5, 10, 15, 20, 50, 100]

# Time periods in days
time_periods = [1, 7, 15]

# Function to calculate fees
def calculate_fees(initial_margin, leverage, annual_rate, days):
    borrowed_amount = initial_margin * (leverage - 1)
    daily_rate = annual_rate / 365
    fee = borrowed_amount * daily_rate * days
    return fee

# Display fees for Marginfi, JUP PERP, and FLASH PERP
for perp_name, annual_rate in [("Marginfi", abs(marginfi['netApy'] * 100)), 
                               ("JUP PERP", jupPerp['jupAnnualRate']), 
                               ("FLASH PERP", flashPerp['flashAnnualRate'])]:
    st.header(f"{perp_name} (APR: {annual_rate:.2f}%)")
    
    # Create a table for each perp
    table_data = []
    for leverage in leverage_levels:
        notional_size_usd = initial_margin_usd * leverage
        notional_size_sol = initial_margin_sol * leverage
        row = [
            f"{leverage}x",
            f"${notional_size_usd:.2f} ({notional_size_sol:.6f} SOL)"
        ]
        for days in time_periods:
            fee_sol = calculate_fees(initial_margin_sol, leverage, annual_rate / 100, days)
            fee_usd = fee_sol * sol_price_usd
            row.append(f"${fee_usd:.2f} ({fee_sol:.6f} SOL)")
        table_data.append(row)
    
    # Display the table
    st.table([["Leverage", "Notional Size", "1 Day", "7 Days", "15 Days"]] + table_data)

st.info("Note: These calculations assume a constant borrow rate and do not account for potential rate changes or compounding effects.")