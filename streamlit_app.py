# requirements.txt に以下を入れてください:
# streamlit>=1.36
# google-genai>=0.3.0
# pypdf>=5.0.0

import json
import streamlit as st
from pypdf import PdfReader

st.set_page_config(page_title="Document QA (Gemini 2.5 Flash)", page_icon="💬")
st.title("Document question answering (Gemini 2.5 Flash)")

# ----- Secrets チェック -----
API_KEY = st.secrets.get("GOOGLE_API_KEY")
if not API_KEY:
    st.error(
        "GOOGLE_API_KEY が見つかりません。Streamlit Cloud の **Manage app → Settings → Secrets** に\n"
        "```\nGOOGLE_API_KEY=\"<あなたのAPIキー>\"\n```\nを追加して、アプリを再実行してください。"
    )
    st.stop()

# ----- google-genai を優先し、失敗時はHTTPにフォールバック -----
use_sdk = True
try:
    from google import genai  # 提供元: google-genai
    client = genai.Client(api_key=API_KEY)
except Exception:
    use_sdk = False

uploaded = st.file_uploader("PDF または TXT をアップロードしてください", type=["pdf", "txt"])
doc_text = ""

if uploaded:
    if uploaded.type == "application/pdf":
        try:
            reader = PdfReader(uploaded)
            pages = [p.extract_text() or "" for p in reader.pages]
            doc_text = "\n\n".join(pages).strip()
            if not doc_text:
                st.warning("このPDFはテキストが抽出できません（画像ベースの可能性）。TXTでお試しください。")
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
        "あなたは与えられた資料のみを根拠に、日本語で簡潔に正確に回答します。\n"
        "回答の最後に、根拠となる抜粋（引用）を箇条書きで示してください。\n\n"
        f"【資料】\n{context}\n\n"
        f"【質問】{q}\n"
    )

def extract_text_from_candidates(obj) -> str:
    """SDK/HTTP どちらのレスポンスでも candidates[0].content.parts[].text を連結して返す"""
    # SDK オブジェクト
    try:
        cand = obj.candidates[0]
        parts = getattr(cand.content, "parts", None)
        if parts:
            return "".join(getattr(p, "text", "") for p in parts if getattr(p, "text", None))
    except Exception:
        pass
    # HTTP の dict
    try:
        cand = obj["candidates"][0]
        parts = cand["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if "text" in p)
    except Exception:
        return ""

if ask and question:
    if not doc_text:
        st.warning("先にドキュメントをアップロードしてください。")
        st.stop()

    # 過剰トークン抑制（必要に応じて増減）
    MAX_CHARS = 120_000
    context = doc_text[:MAX_CHARS]
    prompt = build_prompt(context, question)

    with st.chat_message("assistant"):
        if use_sdk:
            # ---- google-genai（ストリーミング） ----
            contents = [{"role": "user", "parts": [{"text": prompt}]}]
            try:
                stream = client.models.generate_content_stream(
                    model="gemini-2.5-flash",
                    contents=contents,
                )

                def token_stream():
                    for event in stream:
                        if getattr(event, "candidates", None):
                            cand = event.candidates[0]
                            if getattr(cand, "content", None) and getattr(cand.content, "parts", None):
                                for part in cand.content.parts:
                                    if getattr(part, "text", None):
                                        yield part.text

                st.write_stream(token_stream())

            except Exception:
                # 非ストリーミングにフォールバック
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                )
                st.markdown(extract_text_from_candidates(resp) or "_(No content)_")
        else:
            # ---- HTTP 直叩き（非ストリーミング） ----
            import urllib.request, urllib.error

            url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent"
            body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
            req = urllib.request.Request(
                f"{url}?key={API_KEY}",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                st.markdown(extract_text_from_candidates(data) or "_(No content)_")
            except urllib.error.HTTPError as he:
                st.error(f"Gemini HTTP エラー: {he.code} {he.reason}")
            except Exception as e:
                st.error(f"HTTP リクエストに失敗しました: {type(e).__name__}: {e}")
