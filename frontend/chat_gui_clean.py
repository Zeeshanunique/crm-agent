import streamlit as st
import sys
import os

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

st.title("Clean Version Test")
st.write("This is a test file") 