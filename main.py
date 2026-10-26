from datetime import datetime
from lightweight_charts.widgets import StreamlitChart
import numpy as np
import pandas as pd
import streamlit as st

# Page Configuration for Wide Screen & Dark Mode Vibe
st.set_page_config(layout='wide', page_title='R33f3r Terminal - SPX Hybrid')

st.markdown('### R33f3r Trading Terminal: SPX & ES Hybrid Engine')
st.markdown(
    '*(Overnight ES Futures Basis-Shifted + SPX Cash RTH + Heiken Ashi)*'
)


# --- FUNCTION: Build Hybrid Chart Data ---
def process_hybrid_data(es_raw, spy_raw, scale_factor, target_date):
  es = es_raw.copy()
  spy = spy_raw.copy()

  # Clean MultiIndex columns if present
  if isinstance(es.columns, pd.MultiIndex):
    es.columns = es.columns.get_level_values(0)
  if isinstance(spy.columns, pd.MultiIndex):
    spy.columns = spy.columns.get_level_values(0)

  # Align Timezones
  for df in [es, spy]:
    if isinstance(df.index, pd.MultiIndex):
      df.index = df.index.get_level_values(0)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
      df.index = df.index.tz_localize('UTC')
    df.index = df.index.tz_convert('America/New_York')
    df['date'] = pd.DatetimeIndex(df.index).date

  unique_dates = sorted(es['date'].unique())
  if target_date not in unique_dates:
    return None

  idx = unique_dates.index(target_date)
  prev_date = unique_dates[idx - 1] if idx > 0 else target_date

  # Slice ES cycle (overnight)
  es_cycle = es[
      (
          es.index
          >= pd.to_datetime(f'{prev_date} 18:00:00').tz_localize(
              'America/New_York'
          )
      )
      & (
          es.index
          <= pd.to_datetime(f'{target_date} 16:00:00').tz_localize(
              'America/New_York'
          )
      )
  ].copy()
  spy_rth = spy[spy['date'] == target_date].copy()

  if es_cycle.empty or spy_rth.empty:
    return None

  overnight = es_cycle[es_cycle.index.time < pd.to_datetime('09:30').time()]

  # Scale SPY to SPX level
  spy_rth['Close_SPX'] = spy_rth['Close'] * scale_factor
  spy_rth['Open_SPX'] = spy_rth['Open'] * scale_factor
  spy_rth['High_SPX'] = spy_rth['High'] * scale_factor
  spy_rth['Low_SPX'] = spy_rth['Low'] * scale_factor

  # Basis shift calculation at 09:30
  es_open_930 = es_cycle[
      es_cycle.index.time == pd.to_datetime('09:30').time()
  ]['Open'].values[0]
  spy_open_930_spx = spy_rth[
      spy_rth.index.time == pd.to_datetime('09:30').time()
  ]['Open_SPX'].values[0]
  basis_shift = spy_open_930_spx - es_open_930

  # Construct unified series
  hybrid_series = []
  for t, row in overnight.iterrows():
    hybrid_series.append({
        'time': t.strftime('%Y-%m-%d %H:%M:%S'),
        'open': row['Open'] + basis_shift,
        'high': row['High'] + basis_shift,
        'low': row['Low'] + basis_shift,
        'close': row['Close'] + basis_shift,
    })

  for t, row in spy_rth.iterrows():
    hybrid_series.append({
        'time': t.strftime('%Y-%m-%d %H:%M:%S'),
        'open': row['Open_SPX'],
        'high': row['High_SPX'],
        'low': row['Low_SPX'],
        'close': row['Close_SPX'],
    })

  hybrid_df = pd.DataFrame(hybrid_series)
  hybrid_df['time'] = pd.to_datetime(hybrid_df['time'])
  hybrid_df.set_index('time', inplace=True)

  # Compute Heiken Ashi
  ha_close = (
      hybrid_df['open']
      + hybrid_df['high']
      + hybrid_df['low']
      + hybrid_df['close']
  ) / 4.0
  ha_open = [
      (hybrid_df['open'].iloc[0] + hybrid_df['close'].iloc[0]) / 2.0
  ]
  for i in range(1, len(hybrid_df)):
    ha_open.append((ha_open[-1] + ha_close.iloc[i - 1]) / 2.0)

  hybrid_df['open'] = ha_open
  hybrid_df['close'] = ha_close
  hybrid_df['high'] = hybrid_df[['high', 'open', 'close']].max(axis=1)
  hybrid_df['low'] = hybrid_df[['low', 'open', 'close']].min(axis=1)

  # Reset index to simple 'time' column for lightweight-charts
  hybrid_df = hybrid_df.reset_index()
  hybrid_df['time'] = hybrid_df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
  return hybrid_df


# --- STREAMLIT UI & CHART SETUP ---
chart = StreamlitChart(width=1200, height=650, toolbox=True)

# Thinkorswim Dark Theme Styling
chart.layout(background_color='#0b0e11', text_color='#d1d4dc', font_size=12)
chart.candle_style(
    up_color='#00C853',
    down_color='#FF1744',
    border_up_color='#00C853',
    border_down_color='#FF1744',
    wick_up_color='#00C853',
    wick_down_color='#FF1744',
)

# NOTE: Once you load your CSV data variables (es_raw, spy_raw) into GitHub,
# you can call your function like this:
# final_df = process_hybrid_data(es_raw, spy_raw, scale_factor=10, target_date='2026-10-20')
# if final_df is not None:
#     chart.set(final_df)

chart.load()
