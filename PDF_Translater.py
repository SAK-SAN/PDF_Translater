import streamlit as st  #Webアプリのライブラリ
import fitz #PyMuPDF:PDF操作用
import google.generativeai as genai #Gemini API用
from docx import Document   #Word作成用
import time #待ち時間用
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  #.envファイルからAPIキーを取得

st.title("PDF翻訳") #アプリのタイトル
uploaded_file = st.file_uploader("PDFファイルを選択していください", type="pdf") #ファイルの選択

if uploaded_file is not None:
    st.success("ファイルを受け取りました。翻訳を開始します。")

def translate_pdf(pdf_file):
    #pdfからテキストを抽出
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf") #pdfを開く
    full_text = ""
    for page in doc:
        #blocks=Trueにすることで、論文での二段組みなどの構造をある程度考慮して読み取る
        blocks = page.get_text("blocks")
        for b in blocks:
            full_text += b[4] + "\n"    #テキスト内容をfull_textに保持

    #テキストを分割(チャンク化)
    #(GeminiAPIの無料枠のため)
    chunks = [full_text[i:i+2000] for i in range(0, len(full_text), 2000)]

    model = genai.GenerativeModel("gemini-1.5-flash")   #軽量で高速なモデルにする
    translated_text = ""

    #翻訳の実行
    for chunk in chunks:
        prompt = f"以下の英語の論文内容を、全ての文章を一文も余すことなく、専門用語を適切に扱いながら自然な日本語に翻訳してください。また解答は、翻訳した内容のみを生成してください:\n\n{chunk}"
        response = model.generate_content(prompt)   #promptを用いてGeminiに翻訳を依頼
        translated_text += response.text + "\n\n"
        time.sleep(2)   #無料枠の制限(1分間のリクエスト数)に引っかからないように対策
    
    #Wordファイルとして保存
    output_doc = Document()
    output_doc.add_heading("論文和訳結果",0) #見出しを追加
    output_doc.add_paragraph(translated_text)   #翻訳結果を追加

    output_filename = "translated_paper.docx"
    output_doc.save(output_filename)    #ファイルを保存
    return output_filename