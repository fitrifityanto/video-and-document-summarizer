from typing import cast

import streamlit as st
from openai import OpenAI


def get_ai_client() -> OpenAI:
    """Menginisialisasi OpenAI client menggunakan secrets dari Streamlit."""
    try:
        return OpenAI(
            api_key=cast(str, st.secrets["SUMOPOD_API_KEY"]),
            base_url=cast(str, st.secrets["BASE_URL"]),
        )
    except KeyError as e:
        _ = st.error(f"Secret configuration not found: {e}")
        _ = st.stop()


def generate_summary(client: OpenAI, text: str, model: str, temperature: float) -> str:
    """Mengirimkan teks ke AI untuk diringkas ke dalam Bahasa Indonesia."""
    system_prompt = (
        "Anda adalah asisten ahli yang meringkas konten secara mendalam. "
        "Tugas Anda adalah memberikan ringkasan dalam **Bahasa Indonesia** yang sangat detail, "
        "menggunakan poin-poin, menjelaskan konsep utama, dan memberikan kesimpulan akhir yang komprehensif. "
        "Apapun bahasa sumber teksnya, hasil akhir HARUS dalam Bahasa Indonesia."
    )

    user_prompt = f"Tolong buatkan ringkasan mendalam dari teks berikut ke dalam Bahasa Indonesia: {text}"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return str(response.choices[0].message.content)
    except Exception as e:
        raise Exception(f"AI Generation Error: {str(e)}")
