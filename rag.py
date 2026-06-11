import os
from pypdf import PdfReader
from huggingface_hub import InferenceClient

# HF Token ni environment variable nundi read chestundi
HF_TOKEN = os.getenv("HF_TOKEN")

client = InferenceClient(
    HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
)

def ask_pdf(question):

    pdf_folder = "uploads"
    pdf_text = ""

    if not os.path.exists(pdf_folder):
        return "Uploads folder not found."

    for file in os.listdir(pdf_folder):

        if file.endswith(".pdf"):

            reader = PdfReader(os.path.join(pdf_folder, file))

            for page in reader.pages:

                page_text = page.extract_text()

                if page_text:
                    pdf_text += page_text + "\n"

    if pdf_text.strip() == "":
        return "No readable text found in uploaded PDF."
    prompt = f"""
You are a RAG AI Assistant.

Answer ONLY from the uploaded PDF.

If answer exists:
- Give only 3-5 lines.
- Don't copy the whole paragraph.

If answer doesn't exist:
Answer not found in uploaded PDF.

PDF:
{pdf_text}

Question:
{question}
"""    

    try:

        response = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=100
        )

        return response.choices[0].message.content

    except Exception as e:

        return str(e)