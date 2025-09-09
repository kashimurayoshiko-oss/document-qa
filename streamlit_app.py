# requirements:
#   pip install streamlit google-genai

import streamlit as st
from google import genai
from google.genai import types as genai_types

# タイトルと説明
st.title("💬 Chatbot (Gemini 2.5 Flash)")
st.write(
    "このチャットボットは Google の **Gemini 2.5 Flash** を使って応答を生成します。\n\n"
    "利用には Gemini API Key が必要です（Google AI Studio で発行）。"
)

# Gemini API Key 入力欄
gemini_api_key = st.text_input("Gemini API Key", type="password")
if not gemini_api_key:
    st.info("続行するには Gemini API Key を入力してください。", icon="🗝️")
else:
    # Gemini クライアント作成
    client = genai.Client(api_key=gemini_api_key)

    # メッセージ履歴を session_state に保存
    if "messages" not in st.session_state:
        st.session_state.messages = []  # [{"role": "user"|"assistant", "content": "text"}]

    # 既存メッセージを表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 入力欄
    if prompt := st.chat_input("なにを話しますか？"):
        # ユーザーの入力を保存＆表示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Gemini 形式のコンテンツに変換
        contents = []
        for m in st.session_state.messages:
            contents.append(
                genai_types.Content(
                    role="user" if m["role"] == "user" else "model",
                    parts=[genai_types.Part.from_text(m["content"])]
                )
            )

        # Gemini に問い合わせ（ストリーミング）
        with st.chat_message("assistant"):
            stream = client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=contents,
            )

            # トークンを順次表示
            def token_stream():
                for event in stream:
                    if getattr(event, "candidates", None):
                        cand = event.candidates[0]
                        if getattr(cand, "content", None) and getattr(cand.content, "parts", None):
                            for part in cand.content.parts:
                                if getattr(part, "text", None):
                                    yield part.text

            response_text = st.write_stream(token_stream())

        # アシスタント応答を保存
        st.session_state.messages.append({"role": "assistant", "content": response_text})
