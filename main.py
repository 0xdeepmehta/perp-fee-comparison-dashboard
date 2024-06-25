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

# Marginfi data
st.header("Marginfi")
st.write(f"""
- Deposit Token I Rate: {(marginfi['depositTokenIRate'] * 100):.2f}%
- Borrow Token I Rate: {(marginfi['borrowTokenIRate'] * 100):.2f}%
- Annualized Borrow Rate: {(marginfi['netApy'] * 100):.2f}%
""")

# Calculate hourly rates
jup_hourly_rate = jupPerp['jupAnnualRate'] / 8760
flash_hourly_rate = flashPerp['flashAnnualRate'] / 8760

# JUP PERP data
st.header("JUP PERP")
st.write(f"""
- Current LTV: {jupPerp['jupCurrentLTV']} SOL
- Current Borrowed: {jupPerp['jupCurrentBorrowed']} SOL
- Current Utilization: {jupPerp['jupCurrentUtilization']}%
- Borrow Rate per Hour: {jup_hourly_rate:.4f}% / hr
- Annualized Borrow Rate: {jupPerp['jupAnnualRate']:.2f}%
""")

# FLASH PERP data
st.header("FLASH PERP")
st.write(f"""
- Current LTV: {flashPerp['flashCurrentLTV']} SOL
- Current Borrowed: {flashPerp['flashCurrentBorrowed']} SOL
- Current Utilization: {flashPerp['flashCurrentUtilization']}%
- Borrow Rate per Hour: {flash_hourly_rate:.4f}% / hr
- Annualized Borrow Rate: {flashPerp['flashAnnualRate']:.2f}%
""")