import streamlit as st
import pandas as pd
st.set_page_config(layout="wide",
                   page_icon="📉",
                   page_title="xatix",
                   menu_items={
                    'Get Help': 'https://www.extremelycoolapp.com/help',
                    'Report a bug': "https://www.extremelycoolapp.com/bug",
                    'About': "# This is a header. This is an *extremely* cool app!"
                })

dataset = st.session_state['data']
col1, col2 = st.columns(2)

if not dataset is None:
    num_vars = [var for var in dataset.columns if dataset[var].dtypes in ['int','int64'] ]
    cat_vars = [var for var in dataset.columns if dataset[var].dtypes in ["object"]]

    with col1:
        var1 = st.selectbox(label="variable indépendante",
                            options=cat_vars)

    with col2:
        var2 = st.selectbox(label="variable dépendante",
                        options=num_vars)

else:
    with col1:
        var1 = st.selectbox(label="variable 1",
                            options=[],
                            disabled=True)

    with col2:
        var2 = st.selectbox(label="variable 2",
                            options=[],
                            disabled=True)

df = pd.DataFrame()