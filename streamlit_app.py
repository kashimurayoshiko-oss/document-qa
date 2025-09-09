# requirements:
#   streamlit>=1.36
#   google-genai>=0.3.0

import streamlit as st
from google import genai

st.set_page_config(page_title="Gemini 2.5 Flash Chatbot", page_icon="💬")
st.title("💬 Chatbot (Gemini 2.5 Flash)")
st.caption("Google Gemini 2.5 Flash を使ったシンプルなチャットボット")

# ✅ Secrets から安全に取得（未設定なら None）
gemini_api_key = st.secrets.get("GEMINI_API_KEY")

if not gemini_api_key:
    st.error(
        "GEMINI_API_KEY が見つかりません。\n\n"
        "Streamlit Cloud の **Manage app → Settings → Secrets** に以下のように登録してください：\n\n"
        "```\nGEMINI_API_KEY=\"<あなたのAPIキー>\"\n```"
    )
    st.stop()

# クライアント生成
client = genai.Client(api_key=gemini_api_key)

# 会話履歴
if "messages" not in st.session_state:
    st.session_state.messages = []

# 既存メッセージ表示
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# 入力
if prompt := st.chat_input("メッセージを入力..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 直近20件だけ送る（過剰トークン抑制）
    history = st.session_state.messages[-20:]
    contents = [
        {
            "role": "user" if m["role"] == "user" else "model",
            "parts": [{"text": str(m["content"])}],
        }
        for m in history
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

            response_text = st.write_stream(token_stream())
        except Exception:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
            )
            response_text = ""
            if getattr(resp, "candidates", None):
                cand = resp.candidates[0]
                if getattr(cand, "content", None) and getattr(cand.content, "parts", None):
                    response_text = "".join(
                        getattr(p, "text", "") for p in cand.content.parts if getattr(p, "text", None)
                    )
            st.markdown(response_text or "_(No content)_")

    st.session_state.messages.append({"role": "assistant", "content": response_text})
