"""Main Streamlit application entry point."""
import logging
import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

st.set_page_config(
    page_title="AI Content Pipeline",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.ui.components import render_sidebar
from src.ui import research_page, history_page

if "page" not in st.session_state:
    st.session_state["page"] = "main"

render_sidebar()

if st.session_state["page"] == "history":
    history_page.render()
else:
    research_page.render()
