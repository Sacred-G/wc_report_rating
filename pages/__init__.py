import streamlit as st

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select a page:", ["Chat", "History", "Process Report", "Settings", "About"])

if page == "Chat":
    from .chat import chat_interface
    chat_interface(st.session_state.client)  # Assuming client is stored in session state
elif page == "History":
    from .history import history_interface
    history_interface()
elif page == "Process Report":
    from .process_report import process_report_interface
    process_report_interface()
elif page == "Settings":
    from .settings import settings_interface
    settings_interface()
elif page == "About":
    from .about import about_interface
    about_interface()
