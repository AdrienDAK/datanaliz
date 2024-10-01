import streamlit as st
import pandas as pd
from sklearn.linear_model import LinearRegression

dataset = st.session_state['data']
col1, col2, col3 = st.columns(3)

if not dataset is None:
    num_vars = [var for var in dataset.columns if (dataset[var].dtypes in ['int','int64'] and ("ID" not in var) and ("id" not in var) and "Id" not in var)]
    cat_vars = [var for var in dataset.columns if dataset[var].dtypes in ["object"]]

    var1 = num_vars[0]
    var2 = num_vars[1]

    with col1:
        type = st.selectbox(label="Type de régression",
                            index=0,
                            options=["Linéaire", "Logistique"])

    with col2:
        num_choix_3 = list(num_vars)
        num_choix_3.remove(var2)
        var1 = st.selectbox(label="variable dépendante",
                            index=0,
                            options=num_choix_3)

    with col3:
        num_choix_2 = list(num_vars)
        num_choix_2.remove(var1)
        var2 = st.multiselect(label="variable(s) indépendante(s)",
                              options=num_choix_2,
                              placeholder="Choisir une ou plusieurs")

else:
    with col1:
        type = st.selectbox(label="Type de régression",
                            options=[],
                            disabled=True)

    with col2:
        var1 = st.selectbox(label="variable 1",
                            options=[],
                            disabled=True)

    with col3:
        var2 = st.selectbox(label="variable 2",
                            options=[],
                            disabled=True)
lm = LinearRegression()
result = lm.fit(dataset[var1], dataset[var2])
st.write(result)

#df = pd.DataFrame()