# requirements.txt はリポジトリ直下に置き、以下の 2 行だけでOK（SDK不要）
# streamlit>=1.36
# pypdf>=5.0.0

import json
import urllib.request
import urllib.error
import streamlit as st

# PDF 読み取り（画像ベースPDFは抽出不可）
try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ModuleNotFoundError:
    HAS_PYPDF = False

st.set_page_config(page_title="Document QA (Gemini 2.5 Flash)", page_icon="💬")
st.title("Document question answering (Gemini 2.5 Flash)")

# ✅ Secrets から API キー（名前はご指定どおり）
API_KEY = st.secrets.get("GOOGLE_API_KEY")
if not API_KEY:
    st.error(
        "GOOGLE_API_KEY が見つかりません。Streamlit Cloud の **Manage app → Settings → Secrets** に\n"
        'GOOGLE_API_KEY="<あなたのAPIキー>" を登録して再実行してください。'
    )
    st.stop()

# ---- アップローダ（pypdf が無ければ txt のみ許可）----
file_types = ["pdf", "txt"] if HAS_PYPDF else ["txt"]
uploaded = st.file_uploader("PDF または TXT をアップロードしてください", type=file_types)

doc_text = ""
if uploaded:
    if uploaded.name.lower().endswith(".pdf"):
        if not HAS_PYPDF:
            st.error("PDF を扱うには pypdf が必要です。requirements.txt に `pypdf>=5.0.0` を追加して再起動してください。")
            st.stop()
        try:
            reader = PdfReader(uploaded)
            pages = [p.extract_text() or "" for p in reader.pages]
            doc_text = "\n\n".join(pages).strip()
            if not doc_text:
                st.warning("このPDFからはテキストが抽出できません（画像ベースの可能性）。TXT をお試しください。")
        except Exception as e:
            st.error(f"PDF の読み込みに失敗しました: {type(e).__name__}")
            st.stop()
    else:
        doc_text = uploaded.read().decode("utf-8", errors="ignore").strip()

    if doc_text:
        st.success("ドキュメントを読み込みました。質問を入力してください。")

question = st.text_input("質問を入力…")
ask = st.button("Ask")

def build_prompt(context: str, q: str) -> str:
    return (
        "あなたは与えられた資料のみを根拠に、日本語で簡潔かつ正確に回答します。\n"
        "回答の最後に、根拠となる抜粋（引用）を箇条書きで示してください。\n\n"
        f"【資料】\n{context}\n\n"
        f"【質問】{q}\n"
    )

def call_gemini_text(api_key: str, prompt_text: str) -> str:
    """Gemini 2.5 Flash を HTTP で呼び出し、テキストを返す（非ストリーミング）"""
    url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt_text}]}]}
    req = urllib.request.Request(
        f"{url}?key={api_key}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="ignore"))

    # candidates[0].content.parts[].text を連結
    try:
        cand = data["candidates"][0]
        parts = cand["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if "text" in p).strip()
    except Exception:
        return ""

if ask and question:
    if not doc_text:
        st.warning("先にドキュメントをアップロードしてください。")
        st.stop()

    # 過剰トークン抑制（必要に応じて調整）
    MAX_CHARS = 120_000
    context = doc_text[:MAX_CHARS]
    prompt = build_prompt(context, question)

    with st.chat_message("assistant"):
        try:
            answer = call_gemini_text(API_KEY, prompt)
            st.markdown(answer or "_(No content)_")
        except urllib.error.HTTPError as he:
            st.error(f"Gemini HTTP エラー: {he.code} {he.reason}")
            if he.code == 400:
                st.caption("APIキー・モデル名・リクエスト形式をご確認ください。")
        except Exception as e:
            st.error(f"HTTP リクエストに失敗しました: {type(e).__name__}: {e}")
