# requirements.txt（リポジトリ直下）例:
# streamlit>=1.36
# pypdf>=5.0.0

import re, html, json
import urllib.request, urllib.error
import streamlit as st

# --- 基本設定 ---
st.set_page_config(page_title="Document QA (Gemini 2.5 Flash)", page_icon="💬")
st.title("Document question answering (Gemini 2.5 Flash)")

# --- pypdf の有無（PDF用） ---
try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ModuleNotFoundError:
    HAS_PYPDF = False
    st.warning("PDF を処理するには pypdf が必要です。requirements.txt に `pypdf>=5.0.0` を入れてください。", icon="ℹ️")

# --- Secrets（Google の API キー） ---
API_KEY = st.secrets.get("GOOGLE_API_KEY")
if not API_KEY:
    st.error('Secrets に GOOGLE_API_KEY がありません。Manage app → Settings → Secrets で設定してください。')
    st.stop()

# --- ファイル読み込み ---
file_types = ["pdf", "txt"] if HAS_PYPDF else ["txt"]
uploaded = st.file_uploader("PDF または TXT をアップロードしてください", type=file_types)

doc_text = ""
if uploaded:
    if uploaded.name.lower().endswith(".pdf"):
        if not HAS_PYPDF:
            st.error("PDF を扱うには pypdf が必要です。")
            st.stop()
        try:
            reader = PdfReader(uploaded)
            pages = [p.extract_text() or "" for p in reader.pages]
            doc_text = "\n\n".join(pages).strip()
            if not doc_text:
                st.warning("このPDFはテキスト抽出できません（画像主体の可能性）。TXT をお試しください。")
        except Exception as e:
            st.error(f"PDF の読み込みに失敗しました: {type(e).__name__}")
            st.stop()
    else:
        doc_text = uploaded.read().decode("utf-8", errors="ignore").strip()

# --- べきハイライト関数 ---
def underline_beki(text: str) -> str:
    """
    テキスト中の べき表現を <u>…</u> で下線化して返す（HTML）。他の文字は HTML エスケープ。
    対応: するべきではない/すべきではない/べきではない/べきでない/べきではなく/
          べきである/べきだ/するべき/すべき/べき
    """
    # まず全体をエスケープ（<>& を無害化）
    s = html.escape(text)
    # 長いパターン優先でマッチ（重なり防止）
    pattern = re.compile(
        r"(するべきではない|すべきではない|べきではない|べきでない|べきではなく|"
        r"べきである|べきだ|するべき|すべき|べき)"
    )
    return pattern.sub(lambda m: f"<u>{m.group(0)}</u>", s)

# --- Gemini呼び出し（HTTP・非ストリーミング） ---
def call_gemini_text(api_key: str, prompt_text: str) -> str:
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
    try:
        cand = data["candidates"][0]
        parts = cand["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if "text" in p).strip()
    except Exception:
        return ""

# --- UI: タブ ---
tab1, tab2 = st.tabs(["べきハイライト", "ドキュメントQ&A"])

with tab1:
    st.subheader("べき表現を下線表示")
    if not doc_text:
        st.info("上のエリアから PDF または TXT をアップロードしてください。")
    else:
        highlighted = underline_beki(doc_text)
        st.markdown('<div style="white-space:pre-wrap;">' + highlighted + "</div>", unsafe_allow_html=True)
        st.download_button(
            "下線付きHTMLをダウンロード",
            data=('<meta charset="utf-8"><div style="white-space:pre-wrap;">' + highlighted + "</div>").encode("utf-8"),
            file_name="highlighted_beki.html",
            mime="text/html",
        )

with tab2:
    st.subheader("質問に回答（Gemini 2.5 Flash）")
    question = st.text_input("質問を入力…")
    if st.button("Ask"):
        if not doc_text:
            st.warning("先にドキュメントをアップロードしてください。")
        elif not question:
            st.warning("質問を入力してください。")
        else:
            MAX_CHARS = 120_000
            context = doc_text[:MAX_CHARS]
            prompt = (
                "あなたは与えられた資料のみを根拠に、日本語で簡潔かつ正確に回答します。\n"
                "回答の最後に、根拠となる抜粋（引用）を箇条書きで示してください。\n\n"
                f"【資料】\n{context}\n\n"
                f"【質問】{question}\n"
            )
            with st.chat_message("assistant"):
                try:
                    answer = call_gemini_text(API_KEY, prompt)
                    st.markdown(answer or "_(No content)_")
                except urllib.error.HTTPError as he:
                    st.error(f"Gemini HTTP エラー: {he.code} {he.reason}")
