import streamlit as st

st.title('Weather App')

st.write("Welcome to the Israel Public Transit Analytics App 📊 !")


name = st.text_input('Enter your name:', '')
if name:
    st.write(f'Hello {name}!,welcome to Weather App!')


