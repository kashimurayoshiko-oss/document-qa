# streamlit_app.py

import streamlit as st

st.set_page_config(page_title="📄 Document QA (Gemini 2.5 Flash)", page_icon="📄")
st.title("📄 Document question answering (Gemini 2.5 Flash)")
st.write(
    "テキスト/Markdown のドキュメントをアップロードして質問すると、"
    "Google Gemini 2.5 Flash が答えます。APIキーは Streamlit の Secrets に保存してください。"
)

# --- インポート健全性チェック ---
try:
    from google import genai
except Exception as e:
    st.error(
        "`from google import genai` のインポートに失敗しました。\n\n"
        "対応手順：\n"
        "1) リポジトリ直下に **requirements.txt** を作り、次の2行のみを入れる：\n"
        "```\nstreamlit>=1.36\ngoogle-genai>=0.3.0\n```\n"
        "2) プロジェクト直下に `google/` フォルダや `google.py` が無いことを確認（ある場合はリネーム）。\n"
        "3) **Manage app → Reboot app** で再起動。\n\n"
        f"詳細: {type(e).__name__}"
    )
    st.stop()

# --- Secrets チェック ---
gemini_api_key = st.secrets.get("GEMINI_API_KEY")
if not gemini_api_key:
    st.error(
        "GEMINI_API_KEY が見つかりません。Streamlit Cloud の **Manage app → Settings → Secrets** に\n"
        "```\nGEMINI_API_KEY=\"<あなたのAPIキー>\"\n```\nを追加して、アプリを再実行してください。"
    )
    st.stop()

# Gemini クライアント
client = genai.Client(api_key=gemini_api_key)

# ファイルアップロード（.txt / .md）
uploaded_file = st.file_uploader("Upload a document (.txt or .md)", type=("txt", "md"))

# 質問入力
question = st.text_area(
    "Now ask a question about the document!",
    placeholder="Can you give me a short summary?",
    disabled=not uploaded_file,
)

# 実行
if uploaded_file and question:
    # ファイル読み込み（UTF-8 想定・不正バイトは無視）
    raw = uploaded_file.getvalue()
    document_text = raw.decode("utf-8", errors="ignore")

    # 過剰トークン抑制（必要に応じて増減可）
    MAX_CHARS = 120_000
    if len(document_text) > MAX_CHARS:
        document_text = document_text[:MAX_CHARS]
        st.info("ドキュメントが長いため先頭部分のみを使用しました。", icon="ℹ️")

    # Gemini へ渡す内容（辞書形式でSDK差異を回避）
    contents = [
        {
            "role": "user",
            "parts": [{
                "text": (
                    "You are a helpful assistant for document Q&A.\n\n"
                    f"Document:\n{document_text}\n\n---\n\n"
                    f"Question: {question}\n"
                    "Please answer concisely and cite exact snippets when useful."
                )
            }],
        }
    ]

    # 生成（ストリーミング → 失敗時フォールバック）
    with st.chat_message("assistant"):
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
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
            )
            answer = ""
            if getattr(resp, "candidates", None):
                cand = resp.candidates[0]
                if getattr(cand, "content", None) and getattr(cand.content, "parts", None):
                    answer = "".join(
                        getattr(p, "text", "") for p in cand.content.parts if getattr(p, "text", None)
                    )
            st.markdown(answer or "_(No content)_")
