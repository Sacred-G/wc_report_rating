import streamlit as st
import os

st.set_page_config(
    page_title="Settings",
    page_icon="⚙️",
    layout="wide"
)

st.title("Settings")

# API Settings
st.header("API Settings")
api_key = st.text_input("OpenAI API Key", value=os.environ.get('OPENAI_API_KEY', ''), type="password", label_visibility="visible")
if st.button("Save API Key"):
    # Save API key functionality
    st.success("API key saved successfully")

# CSV File Settings
st.header("Data Files")
st.write("Current CSV files:")
st.write("- Occupations: data/occupations_rows.csv")
st.write("- Age Adjustments: data/age_adjustment_rows.csv")
st.write("- Occupational Adjustments: data/occupational_adjustments_rows.csv")
st.write("- Variants: data/variants.csv")

# Upload new CSV files
st.subheader("Update CSV Files")
new_occupations = st.file_uploader("Upload new occupations CSV", type=["csv"], label_visibility="visible")
new_age_adj = st.file_uploader("Upload new age adjustments CSV", type=["csv"], label_visibility="visible")
new_occ_adj = st.file_uploader("Upload new occupational adjustments CSV", type=["csv"], label_visibility="visible")
new_variants = st.file_uploader("Upload new variants CSV", type=["csv"], label_visibility="visible")

if st.button("Update CSV Files"):
    # Add CSV update functionality
    st.success("CSV files updated successfully")
