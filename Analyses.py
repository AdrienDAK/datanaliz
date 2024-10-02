import streamlit as st
import pandas as pd

from langchain.llms import OpenAI

st.set_page_config(layout="wide",
                   page_icon="📉",
                   page_title="xatix",
                   menu_items={
                    'Get Help': 'https://www.extremelycoolapp.com/help',
                    'Report a bug': "https://www.extremelycoolapp.com/bug",
                    'About': "# This is a header. This is an *extremely* cool app!"
                })



dataset = None
if "data" not in st.session_state:
    st.session_state['data'] = None

if not (st.session_state['data'] is None):
    dataset = st.session_state['data']

uploaded_file = st.sidebar.file_uploader(label="",
                type=["xlsx", "csv", "xls"],
                label_visibility="collapsed")

if not (uploaded_file is None):
    file = uploaded_file.getvalue()
    dataset = pd.read_excel(file)
    st.session_state['data'] = dataset
if not dataset is None:
    displayed_data = st.data_editor(dataset)

    with st.popover("Save the file"):
        st.markdown("Name the file")
        name = st.text_input("Write a name")

else:
    st.write("-- There are no data to display --")

st.sidebar.markdown("--------------------")
st.sidebar.markdown("Rapports")
st.sidebar.button("Nouveau Rapport")

OpenAI_API_Key = "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"



openai_api_key = st.sidebar.text_input(OpenAI_API_Key)

def generate_response(input_text):
  llm = OpenAI(temperature=0.7, openai_api_key=openai_api_key)
  st.info(llm(input_text))

with st.form('my_form'):
  text = st.text_area('Enter text:', 'What are the three key pieces of advice for learning how to code?')
  submitted = st.form_submit_button('Submit')
  if not openai_api_key.startswith('sk-'):
    st.warning('Please enter your OpenAI API key!', icon='⚠')
  if submitted and openai_api_key.startswith('sk-'):
    generate_response(text)
