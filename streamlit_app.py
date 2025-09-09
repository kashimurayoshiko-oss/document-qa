# --- pypdf の有無（PDF用） ---
try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ModuleNotFoundError:
    HAS_PYPDF = False
    # ← 初期表示の警告は出さない（PDFを選んだ時だけ出す）

# --- アップロード ---
file_types = ["pdf", "txt"] if HAS_PYPDF else ["txt"]
uploaded = st.file_uploader("PDF または TXT をアップロードしてください", type=file_types)

# ★ 直接貼り付け欄（これを追加）
manual_text = st.text_area("またはテキストを直接貼り付け", height=160, placeholder="ここに本文を貼り付けてもOK")

doc_text = ""

if uploaded:
    # 空ファイル対策
    if getattr(uploaded, "size", None) == 0:
        st.warning("アップロードされたファイルが空（0バイト）です。内容を入れて保存してからアップロードしてください。")
    elif uploaded.name.lower().endswith(".pdf"):
        if not HAS_PYPDF:
            st.error("PDF を処理するには pypdf>=5.0.0 が必要です。requirements.txt に追加して Reboot してください。")
            st.stop()
        try:
            reader = PdfReader(uploaded)
            pages = [p.extract_text() or "" for p in reader.pages]
            doc_text = "\n\n".join(pages).strip()
            if not doc_text:
                st.warning("このPDFはテキスト抽出できません（画像主体の可能性）。TXT か貼り付けでお試しください。")
        except Exception as e:
            st.error(f"PDF の読み込みに失敗しました: {type(e).__name__}")
            st.stop()
    else:
        doc_text = uploaded.read().decode("utf-8", errors="ignore").strip()

# ★ 貼り付けがあれば貼り付けを優先
if manual_text and manual_text.strip():
    doc_text = manual_text.strip()
