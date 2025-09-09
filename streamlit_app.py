# requirements:
#   streamlit>=1.36
#   google-genai>=0.3.0

import streamlit as st
from google import genai

st.set_page_config(page_title="Gemini 2.5 Flash Chatbot", page_icon="💬")
st.title("💬 Chatbot (Gemini 2.5 Flash)")
st.caption("Google Gemini 2.5 Flash を使ったシンプルなチャットボット")

# ✅ Secrets から APIキーを取得（.streamlit/secrets.toml または Cloud の Secrets 設定から）
gemini_api_key = st.secrets["GEMINI_API_KEY"]

# クライアント生成
client = genai.Client(api_key=gemini_api_key)

# 会話履歴を保持
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role":"user"|"assistant","content":"..."}]

# 既存メッセージ表示
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# 入力
if prompt := st.chat_input("メッセージを入力..."):
    # ユーザー発話を保存＆表示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 過去ログを直近20件に制限
    history = st.session_state.messages[-20:]

    contents = []
    for m in history:
        contents.append({
            "role": "user" if m["role"] == "user" else "model",
            "parts": [{"text": str(m["content"])}],
        })

    # Gemini に問い合わせ（ストリーミング）
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
            # フォールバック: 非ストリーミング呼び出し
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

    # 応答を履歴に保存
    st.session_state.messages.append({"role": "assistant", "content": response_text})
