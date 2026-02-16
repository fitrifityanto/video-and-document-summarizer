import streamlit as st


def display_summary_and_download(content: str, file_prefix: str):
    """Helper function to display the summary and a download button."""
    _ = st.success("Selesai!")
    _ = st.markdown(content)

    _ = st.download_button(
        label="📥 Download Summary (.md)",
        data=content,
        file_name=f"summary_{file_prefix}.md",
        mime="text/markdown",
    )
