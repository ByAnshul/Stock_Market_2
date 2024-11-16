import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import ta
from streamlit_autorefresh import st_autorefresh
import time

# Mapping of stock tickers to names
stock_names = {
    'AAPL': 'Apple Inc.',
    'GOOGL': 'Alphabet Inc.',
    'MSFT': 'Microsoft Corporation',
    'AMZN': 'Amazon.com Inc.',
    'TSLA': 'Tesla Inc.',
    'NFLX': 'Netflix Inc.',
    'NVDA': 'NVIDIA Corporation',
    'META': 'Meta Platforms, Inc.',
    'BABA': 'Alibaba Group Holding Ltd.',
    'ADBE': 'Adobe Inc.',
    'INTC': 'Intel Corporation',
    'RELIANCE.NS': 'Reliance Industries Limited',
    'TCS.NS': 'Tata Consultancy Services',
}

# Fetch stock data based on the ticker, period, and interval
def fetch_stock_data(ticker, period, interval):
    try:
        end_date = datetime.now()
        if period == '1wk':
            start_date = end_date - timedelta(days=7)
            data = yf.download(ticker, start=start_date, end=end_date, interval=interval)
        elif period == '1d':
            data = yf.download(ticker, period='1d', interval=interval)
        else:
            data = yf.download(ticker, period=period, interval=interval)
        if data.empty:
            st.warning(f"No data found for {ticker}. It may be delisted or there is no price data available.")
            return None
        return data
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {e}")
        return None

# Process data to ensure it is timezone-aware and has the correct format
def process_data(data):
    if data.index.tzinfo is None:
        data.index = data.index.tz_localize('UTC')
    data.index = data.index.tz_convert('US/Eastern')
    data.reset_index(inplace=True)
    data.rename(columns={'Date': 'Datetime'}, inplace=True)
    return data

# Calculate basic metrics from the stock data
def calculate_metrics(data):
    last_close = data['Close'].iloc[-1]
    prev_close = data['Close'].iloc[0]
    change = last_close - prev_close
    pct_change = (change / prev_close) * 100
    high = data['High'].max()
    low = data['Low'].min()
    volume = data['Volume'].sum()
    return last_close, change, pct_change, high, low, volume

# Add simple moving average (SMA) and exponential moving average (EMA) indicators
def add_technical_indicators(data):
    data['SMA_20'] = ta.trend.sma_indicator(data['Close'], window=20)
    data['EMA_20'] = ta.trend.ema_indicator(data['Close'], window=20)
    return data

# Adding RSI and MACD
def add_more_indicators(data):
    data['RSI'] = ta.momentum.rsi(data['Close'], window=14)
    data['MACD'] = ta.trend.macd(data['Close'])
    data['MACD_Signal'] = ta.trend.macd_signal(data['Close'])
    return data

# Set up Streamlit page layout
st.set_page_config(layout="wide")
st.title('Real Time Stock Dashboard')

# Sidebar for user input parameters
st.sidebar.header('Chart Parameters')
ticker = st.sidebar.selectbox('Select Ticker', list(stock_names.keys()), index=0)
time_period = st.sidebar.selectbox('Time Period', ['1d', '1wk', '1mo', '1y', 'max'])

# Enhanced Interval Selection
custom_intervals = ['1m', '5m', '15m', '30m', '1h', '1d', '1wk']
interval = st.sidebar.selectbox('Data Interval', custom_intervals)
chart_type = st.sidebar.selectbox('Chart Type', ['Candlestick', 'Line'])
indicators = st.sidebar.multiselect('Technical Indicators', ['SMA 20', 'EMA 20', 'RSI', 'MACD'])

# Sidebar option for stock comparison
st.sidebar.subheader("Compare Stocks")
compare_ticker = st.sidebar.selectbox("Select Ticker to Compare", list(stock_names.keys()))

# Auto-refresh logic (refresh every 10 seconds) and countdown
refresh_interval = 20
st_autorefresh(interval=refresh_interval * 1000, key="datarefresh")
last_refresh_time = time.time()
time_since_refresh = int(time.time() - last_refresh_time)
countdown = refresh_interval - time_since_refresh
st.sidebar.write(f"Auto-refresh in {countdown} seconds")

# MAIN CONTENT AREA
data = fetch_stock_data(ticker, time_period, interval)
if data is not None:
    data = process_data(data)
    data = add_technical_indicators(data)
    data = add_more_indicators(data)
    last_close, change, pct_change, high, low, volume = calculate_metrics(data)

    # Display main metrics
    st.metric(label=f"{stock_names[ticker]} Last Price", value=f"{last_close:.2f} USD", delta=f"{change:.2f} ({pct_change:.2f}%)")
    coll, col2, col3 = st.columns(3)
    coll.metric("High", f"{high:.2f} USD")
    col2.metric("Low", f"{low:.2f} USD")
    col3.metric("Volume", f"{volume:,}")

    # Plot the stock price chart
    fig = go.Figure()
    if chart_type == 'Candlestick':
        fig.add_trace(go.Candlestick(
            x=data['Datetime'],
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close']
        ))
    else:
        fig.add_trace(go.Scatter(x=data['Datetime'], y=data['Close'], mode='lines', name='Close Price'))

    # Add selected technical indicators to the chart
    for indicator in indicators:
        if indicator == 'SMA 20':
            fig.add_trace(go.Scatter(x=data['Datetime'], y=data['SMA_20'], name='SMA 20'))
        elif indicator == 'EMA 20':
            fig.add_trace(go.Scatter(x=data['Datetime'], y=data['EMA_20'], name='EMA 20'))
        elif indicator == 'RSI':
            st.subheader('RSI Indicator')
            st.line_chart(data['RSI'])
        elif indicator == 'MACD':
            st.subheader('MACD Indicator')
            st.line_chart(data[['MACD', 'MACD_Signal']])

    # Format graph
    fig.update_layout(title=f'{stock_names[ticker]} {time_period.upper()} Chart',
                      xaxis_title='Time',
                      yaxis_title='Price (USD)',
                      height=680)
    st.plotly_chart(fig, use_container_width=True)

    # Display historical data and technical indicators
    st.subheader('Historical Data')
    st.dataframe(data[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']])
    st.subheader('Technical Indicators')
    st.dataframe(data[['Datetime', 'SMA_20', 'EMA_20', 'RSI', 'MACD', 'MACD_Signal']])

    # Download data as CSV
    st.download_button(
        label="Download Data as CSV",
        data=data.to_csv().encode('utf-8'),
        file_name=f'{ticker}_data.csv',
        mime='text/csv'
    )

# Stock comparison chart
compare_data = fetch_stock_data(compare_ticker, time_period, interval)
if compare_data is not None:
    compare_data = process_data(compare_data)
    fig_compare = go.Figure()
    fig_compare.add_trace(go.Scatter(x=data['Datetime'], y=data['Close'], name=f"{ticker} Close Price"))
    fig_compare.add_trace(go.Scatter(x=compare_data['Datetime'], y=compare_data['Close'], name=f"{compare_ticker} Close Price"))
    fig_compare.update_layout(title=f'Comparison of {stock_names[ticker]} and {stock_names[compare_ticker]}',
                              xaxis_title='Time',
                              yaxis_title='Price (USD)',
                              height=680)
    st.plotly_chart(fig_compare, use_container_width=True)

# Sidebar section for real-time stock prices of selected symbols
st.sidebar.header('Real-Time Stock Prices')
for symbol in stock_names.keys():
    real_time_data = fetch_stock_data(symbol, '1d', '1m')
    if real_time_data is not None and not real_time_data.empty:
        real_time_data = process_data(real_time_data)
        last_price = real_time_data['Close'].iloc[-1]
        change = last_price - real_time_data['Open'].iloc[0]
        pct_change = (change / real_time_data['Open'].iloc[0]) * 100
        st.sidebar.metric(f"{stock_names[symbol]}", f"{last_price:.2f} USD", f"{change:.2f} ({pct_change:.2f}%)")

# Sidebar information section
st.sidebar.subheader('About')
st.sidebar.info('This dashboard provides stock data and technical indicators for various time periods. Use the sidebar to customize your view.')