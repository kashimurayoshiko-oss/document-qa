import streamlit as st
from google import genai
from pypdf import PdfReader

st.set_page_config(page_title="Document QA (Gemini)", page_icon="💬")
st.title("Document question answering (Gemini)")

# APIキーは Secrets に GOOGLE_API_KEY として保存しておく
client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])

uploaded = st.file_uploader("PDF または TXT をアップロードしてください", type=["pdf", "txt"])
doc_text = ""

if uploaded:
    if uploaded.type == "application/pdf":
        reader = PdfReader(uploaded)
        pages = [p.extract_text() or "" for p in reader.pages]
        doc_text = "\n\n".join(pages)
    else:
        doc_text = uploaded.read().decode("utf-8", errors="ignore")
    st.success("ドキュメントを読み込みました。質問を入力してください。")

question = st.text_input("質問を入力…")
if st.button("Ask") and question:
    if not doc_text:
        st.warning("先にドキュメントをアップロードしてください。")
    else:
        context = doc_text[:120000]
        prompt = f"""あなたは与えられた資料のみを根拠に日本語で簡潔に答えます。
資料:
{context}

質問: {question}
根拠も一緒に示してください。"""
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        st.write(resp.text)
