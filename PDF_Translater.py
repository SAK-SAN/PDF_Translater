import streamlit as st  #Webアプリのライブラリ
import fitz #PyMuPDF:PDF操作用
from google import genai
from docx import Document   #Word作成用
import time #待ち時間用
import os
from dotenv import load_dotenv
import random

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")) #.envファイルからAPIキーを取得

st.title("PDF翻訳") #アプリのタイトル
uploaded_file = st.file_uploader("PDFファイルを選択していください", type="pdf") #ファイルの選択

def translate_pdf(pdf_file):
    #pdfからテキストを抽出
    pdf_file.seek(0)
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf") #pdfを開く
    full_text = ""
    for page in doc:
        #blocks=Trueにすることで、論文での二段組みなどの構造をある程度考慮して読み取る
        blocks = page.get_text("blocks")
        for b in blocks:
            full_text += b[4] + "\n"    #テキスト内容をfull_textに保持

    #テキストを分割(チャンク化)
    #(GeminiAPIの無料枠のため)
    chunks = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]

    translated_text = ""

    progress_text = "翻訳中..."
    my_bar = st.progress(0, text=progress_text)

    #翻訳の実行
    for i, chunk in enumerate(chunks):
        success = False #翻訳が成功したかどうかのフラグ
        retries = 0 #試行回数
        max_retries = 10 #10回までは再試行する
        prompt = f"以下の英語の論文内容を、全ての文章を一文も余すことなく、専門用語を適切に扱いながら自然な日本語に翻訳してください。また解答は、翻訳した内容のみを生成してください:\n\n{chunk}"
        while not success and retries < max_retries:
            try:
                response = client.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=prompt
                )
                translated_text += response.text + "\n\n"
                success = True #成功したらループを抜ける

            except Exception as e:
                if "503" in str(e) or "429" in str(e):
                    retries += 1
                    #待機時間を少しずつ増やす
                    wait_time = (2 ** retries) + random(0,1) + 5
                    st.warning(f"サーバー混雑中... {wait_time:.1f}秒後に再試行します ({i+1}/{len(chunks)})")
                    time.sleep(wait_time)
                else:
                    st.error(f"予期せぬエラー:{e}")
                    raise e

        #進捗更新
        progress = (i + 1) / len(chunks)
        my_bar.progress(progress, text=f"{progress_text} ({i+1}/{len(chunks)} 完了)")


        time.sleep(5)   #無料枠の制限(1分間のリクエスト数)に引っかからないように対策
    
    #Wordファイルとして保存
    output_doc = Document()
    output_doc.add_heading("論文和訳結果",0) #見出しを追加
    for line in translated_text.split("\n"):
        if line.strip():
            output_doc.add_paragraph(line)

    output_filename = "translated_paper.docx"
    output_doc.save(output_filename)    #ファイルを保存
    return output_filename

if uploaded_file is not None:
    st.info("ファイルがアップロードされました。下のボタンを押すと翻訳を開始します。")
    
    if st.button("翻訳を開始"):
        with st.spinner("AIが思考中..."):
            try:
                result_file = translate_pdf(uploaded_file)
                st.success("翻訳が完了しました！")
                
                # --- 5. ダウンロードボタンを設置 ---
                with open(result_file, "rb") as f:
                    st.download_button(
                        label="翻訳後のWordファイルをダウンロード",
                        data=f,
                        file_name=result_file,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")