"""MARTIQ - Dataset Analysis

Analyzes the bundled SuperMarket Analysis.csv dataset with Pandas and Plotly.
Users can also upload a CSV/XLSX file for the same analysis workflow.
"""
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
import config
from utils import ui


def _load_file(uploaded):
    if uploaded is None:
        path=Path(config.DATASET_PATH)
        if not path.exists(): return None
        return pd.read_csv(path)
    return pd.read_csv(uploaded) if uploaded.name.lower().endswith('.csv') else pd.read_excel(uploaded)

def _clean(df):
    df=df.copy(); before=len(df)
    df.columns=[str(c).strip() for c in df.columns]
    df=df.drop_duplicates()
    numeric=['Unit price','Quantity','Tax 5%','Sales','cogs','gross margin percentage','gross income','Rating']
    for c in numeric:
        if c in df.columns: df[c]=pd.to_numeric(df[c], errors='coerce')
    if 'Date' in df.columns: df['Date']=pd.to_datetime(df['Date'], errors='coerce')
    df=df.dropna(subset=[c for c in ['Sales','Quantity'] if c in df.columns])
    return df, before-len(df)

def render():
    ui.page_header('📈','Data Analysis','Analyze the supermarket dataset using Python, Pandas and interactive charts')
    st.info('The bundled **SuperMarket Analysis.csv** is loaded by default. You can upload another CSV/XLSX file to analyze it with the same workflow.')
    uploaded=st.file_uploader('Upload Dataset (CSV/XLSX)', type=['csv','xlsx'], key='dataset_analysis_upload')
    df=_load_file(uploaded)
    if df is None:
        st.error('Dataset file not found. Place SuperMarket Analysis.csv inside the data folder.')
        return
    clean_df, removed=_clean(df)
    st.caption(f'Rows: {len(clean_df):,} · Columns: {len(clean_df.columns)} · Duplicate/invalid rows removed: {removed:,}')
    if clean_df.empty: st.warning('No usable rows after cleaning.'); return
    c1,c2,c3,c4=st.columns(4)
    if 'Sales' in clean_df: c1.metric('Total Sales',f"₹{clean_df['Sales'].sum():,.2f}")
    if 'Quantity' in clean_df: c2.metric('Units Sold',f"{clean_df['Quantity'].sum():,.0f}")
    if 'gross income' in clean_df: c3.metric('Gross Income',f"₹{clean_df['gross income'].sum():,.2f}")
    if 'Rating' in clean_df: c4.metric('Avg Rating',f"{clean_df['Rating'].mean():.2f}")
    st.markdown('---')
    tab1,tab2,tab3=st.tabs(['📊 Overview','📉 Visualizations','💡 Business Insights'])
    with tab1:
        st.markdown('#### Cleaned Dataset Preview')
        st.dataframe(clean_df.head(50),use_container_width=True,hide_index=True)
        st.markdown('#### Summary Statistics')
        st.dataframe(clean_df.describe(include='all').transpose(),use_container_width=True)
    with tab2:
        if {'Product line','Sales'}.issubset(clean_df.columns):
            d=clean_df.groupby('Product line',as_index=False)['Sales'].sum().sort_values('Sales',ascending=False)
            st.plotly_chart(px.bar(d,x='Product line',y='Sales',title='Sales by Product Line'),use_container_width=True)
        if {'Branch','Sales'}.issubset(clean_df.columns):
            d=clean_df.groupby('Branch',as_index=False)['Sales'].sum()
            st.plotly_chart(px.bar(d,x='Branch',y='Sales',title='Sales by Branch'),use_container_width=True)
        if {'Payment','Sales'}.issubset(clean_df.columns):
            d=clean_df.groupby('Payment',as_index=False)['Sales'].sum()
            st.plotly_chart(px.pie(d,names='Payment',values='Sales',title='Sales by Payment Method',hole=.4),use_container_width=True)
        if {'Gender','Sales'}.issubset(clean_df.columns):
            d=clean_df.groupby('Gender',as_index=False)['Sales'].sum()
            st.plotly_chart(px.bar(d,x='Gender',y='Sales',title='Sales by Gender'),use_container_width=True)
        if {'Date','Sales'}.issubset(clean_df.columns):
            d=clean_df.groupby('Date',as_index=False)['Sales'].sum().sort_values('Date')
            st.plotly_chart(px.line(d,x='Date',y='Sales',title='Daily Sales Trend'),use_container_width=True)
    with tab3:
        insights=[]
        if {'Product line','Sales'}.issubset(clean_df.columns):
            r=clean_df.groupby('Product line')['Sales'].sum().sort_values(ascending=False); insights.append(f"Top product line by sales: **{r.index[0]}** (₹{r.iloc[0]:,.2f}).")
        if {'Branch','Sales'}.issubset(clean_df.columns):
            r=clean_df.groupby('Branch')['Sales'].sum().sort_values(ascending=False); insights.append(f"Highest-sales branch: **{r.index[0]}** (₹{r.iloc[0]:,.2f}).")
        if {'Payment','Sales'}.issubset(clean_df.columns):
            r=clean_df.groupby('Payment')['Sales'].sum().sort_values(ascending=False); insights.append(f"Highest-sales payment method: **{r.index[0]}**.")
        if 'gross income' in clean_df.columns: insights.append(f"Total gross income in the dataset: **₹{clean_df['gross income'].sum():,.2f}**.")
        if 'Rating' in clean_df.columns: insights.append(f"Average customer rating: **{clean_df['Rating'].mean():.2f}/10**.")
        for x in insights: st.markdown('• '+x)
        st.download_button('📥 Download Cleaned Dataset',clean_df.to_csv(index=False).encode('utf-8'),'martiq_cleaned_dataset.csv','text/csv')
