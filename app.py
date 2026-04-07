import json
import os

import anthropic
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-5"
SYSTEM = """Sei un assistente che analizza recensioni di clienti.
Per ogni recensione rispondi SOLO con un oggetto JSON valido (nessun markdown, nessun testo fuori dal JSON) con queste chiavi esatte:
- "sentiment": una tra "positivo", "negativo", "neutro"
- "problema_principale": stringa breve; se non c'è un problema chiaro, stringa vuota ""
- "risposta_suggerita": testo breve e professionale da inviare al cliente"""

SENTIMENT_COLORS = {
    "positivo": "#16a34a",
    "negativo": "#dc2626",
    "neutro": "#ca8a04",
}


def strip_code_fence(raw: str) -> str:
    raw = raw.strip()
    if not raw.startswith("```"):
        return raw
    lines = raw.split("\n")
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def analyze_review(client: anthropic.Anthropic, testo: str) -> dict:
    user_msg = f"Analizza questa recensione e restituisci solo il JSON richiesto:\n\n{testo}"
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = "".join(block.text for block in response.content if hasattr(block, "text"))
    parsed = json.loads(strip_code_fence(raw))
    return {
        "sentiment": parsed.get("sentiment", "").strip().lower(),
        "problema_principale": parsed.get("problema_principale", ""),
        "risposta_suggerita": parsed.get("risposta_suggerita", ""),
    }


def render_result(item: dict, idx: int) -> None:
    analisi = item.get("analisi") or {}
    sentiment = analisi.get("sentiment", "")
    color = SENTIMENT_COLORS.get(sentiment, "#6b7280")
    st.markdown(f"### Recensione {idx}")
    st.write(item.get("recensione", ""))
    st.markdown(
        f"**Sentiment:** <span style='color:{color};font-weight:700'>{sentiment or 'n/d'}</span>",
        unsafe_allow_html=True,
    )
    st.write(f"**Problema principale:** {analisi.get('problema_principale', '') or 'Nessuno'}")
    st.write(f"**Risposta suggerita:** {analisi.get('risposta_suggerita', '') or 'N/D'}")
    if item.get("errore"):
        st.error(f"Errore analisi: {item['errore']}")
    st.divider()


def main() -> None:
    st.set_page_config(page_title="Analizzatore di Recensioni AI", page_icon="⭐", layout="wide")
    st.title("Analizzatore di Recensioni AI")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("Manca ANTHROPIC_API_KEY nel file .env.")
        st.stop()

    st.write("Incolla una recensione per riga e clicca **Analizza**.")
    text_input = st.text_area(
        "Recensioni (una per riga)",
        height=220,
        placeholder="Servizio ottimo e tempi rapidi.\nConsegna in ritardo e pacco rovinato.",
    )

    if "results" not in st.session_state:
        st.session_state["results"] = []

    if st.button("Analizza", type="primary"):
        reviews = [line.strip() for line in text_input.splitlines() if line.strip()]
        if not reviews:
            st.warning("Inserisci almeno una recensione.")
        else:
            client = anthropic.Anthropic(api_key=api_key)
            output = []
            progress = st.progress(0, text="Analisi in corso...")
            for i, review in enumerate(reviews, start=1):
                try:
                    analisi = analyze_review(client, review)
                    output.append({"recensione": review, "analisi": analisi})
                except Exception as exc:
                    output.append({"recensione": review, "analisi": None, "errore": str(exc)})
                progress.progress(i / len(reviews), text=f"Analizzate {i}/{len(reviews)} recensioni")

            st.session_state["results"] = output
            progress.empty()
            st.success("Analisi completata.")

    results = st.session_state.get("results", [])
    if results:
        st.subheader("Risultati")
        for idx, item in enumerate(results, start=1):
            render_result(item, idx)

        json_data = json.dumps(results, ensure_ascii=False, indent=2)
        st.download_button(
            label="Scarica risultati JSON",
            data=json_data,
            file_name="output.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
