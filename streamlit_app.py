# requirements:
#   streamlit>=1.36
#   google-genai>=0.3.0

import os
import streamlit as st
from google import genai
from google.genai import types as genai_types

st.set_page_config(page_title="Gemini 2.5 Flash Chatbot", page_icon="💬")
st.title("💬 Chatbot (Gemini 2.5 Flash)")
st.caption("Google Gemini 2.5 Flash を使ったシンプルなチャットボット")

# Secrets から読み取り（Cloud では「⚙️ Manage app」> Secrets に保存推奨）
default_key = st.secrets.get("GEMINI_API_KEY", "")
gemini_api_key = st.text_input("Gemini API Key", value=default_key, type="password")

if not gemini_api_key:
    st.info("GEMINI_API_KEY を入力（または Secrets に設定）してください。", icon="🗝️")
    st.stop()

# クライアント生成
client = genai.Client(api_key=gemini_api_key)

# 会話履歴
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role":"user"|"assistant","content":"..."}]

# 既存メッセージを表示
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# 入力
if prompt := st.chat_input("メッセージを入力..."):
    # ユーザー発話を保存＆表示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gemini 形式へ変換
    contents = [
        genai_types.Content(
            role=("user" if m["role"] == "user" else "model"),
            parts=[genai_types.Part.from_text(m["content"])]
        )
        for m in st.session_state.messages
    ]

    # 生成（ストリーミング）
    with st.chat_message("assistant"):
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

    # 応答を履歴に保存
    st.session_state.messages.append({"role": "assistant", "content": response_text})
