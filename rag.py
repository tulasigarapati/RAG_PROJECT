import os
from pypdf import PdfReader
from huggingface_hub import InferenceClient


client = InferenceClient(
    token=os.getenv("HUGGINGFACEHUB_API_TOKEN")
)


def ask_pdf(question):

    pdf_folder = "uploads"
    pdf_text = ""

    if not os.path.exists(pdf_folder):
        return "Uploads folder not found."

    # Read PDFs
    for file in os.listdir(pdf_folder):

        if file.endswith(".pdf"):

            reader = PdfReader(os.path.join(pdf_folder, file))

            for page in reader.pages:

                text = page.extract_text()

                if text:
                    pdf_text += text + "\n"

    if pdf_text.strip() == "":
        return "No readable text found."

    # -------- LIMIT CONTEXT SIZE --------
    MAX_CHARS = 12000

    if len(pdf_text) > MAX_CHARS:
        pdf_text = pdf_text[:MAX_CHARS]
    # -----------------------------------

    prompt = f"""
You are an AI assistant.

Answer ONLY using the PDF content below.

If the answer is present:
- Answer in 3-5 lines.
- Summarize, don't copy large paragraphs.

If the answer is not present:
Answer not found in uploaded PDF.

PDF Content:
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