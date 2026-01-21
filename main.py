import streamlit as st

st.title('Weather App')

name = st.text_input('Enter your name:', '')
if name:
    st.write(f'Hello {name}!,welcome to Weather App!')