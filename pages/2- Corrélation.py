import streamlit as st
import pandas as pd
from scipy.stats import pearsonr
import matplotlib.pyplot as plt

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

    var1 = num_vars[0]
    var2 = num_vars[1]

    with col1:
        num_choix_1 = list(num_vars)
        num_choix_1.remove(var2)
        var1 = st.selectbox(label="variable 1",
                            options=num_choix_1)

    with col2:
        num_choix_2 = list(num_vars)
        num_choix_2.remove(var1)
        var2 = st.selectbox(label="variable 2",
                            options=num_choix_2)

    corr,p = pearsonr(dataset[var1], dataset[var2])
    df = pd.DataFrame({
                        "Résultats":["Valeurs"],
                        'coef':[corr],
                        "p-value":[format(float(p), ".4f")]
                        }).set_index("Résultats")

    st.write(df)
    width = len(dataset[var1])
    st.scatter_chart(data=dataset, x=var1, y=var2)

else:
    with col1:
        var1 = st.selectbox(label="variable 1",
                            options=[],
                            disabled=True)

    with col2:
        var2 = st.selectbox(label="variable 2",
                            options=[],
                            disabled=True)