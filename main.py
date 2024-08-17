import streamlit as st
from openai import OpenAI
import os
import base64
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO
import pandas as pd
import genanki
import io
from pdf2image import convert_from_bytes
import numpy as np
import pytesseract
from pytesseract import Output, TesseractError



client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_KEY"),
)


# Testing
def images_to_txt(path, language):
    images = convert_from_bytes(path)
    all_text = []
    for i in images:
        text = pytesseract.image_to_string(i, lang="eng")
        all_text.append(text)
    return all_text

def get_txt(path):
    texts = images_to_txt(path, "en")
    text_data_f = "\n\n".join(texts)
    return text_data_f




def see_notes(file):
  base64_pdf = base64.b64encode(file).decode('utf-8')
  pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
  st.markdown(pdf_display, unsafe_allow_html=True)

def generate_flashcards(text):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a GPT that automatically generates flashcards given someone's uploaded notes. The question and answers are to be semi-colon separated in the order question, answer. Each question, answer pair is to be on a separate line"},
            {"role": "user", "content": f"Generate flashcards from the following notes: {text}"}
        ]
    )
    return response.choices[0].message.content

def convert_pdf_to_txt_file(path):
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    
    for page in PDFPage.get_pages(path):
      interpreter.process_page(page)
      t = retstr.getvalue()

    device.close()
    retstr.close()
    return t

def digital_text(notes):
    text_data_f = convert_pdf_to_txt_file(notes)
    return text_data_f

def get_df(flashcards):
    statements = flashcards.split("\n")

    # Initialize an empty list to store the dictionaries
    result_dict = {}

    # Iterate over each statement
    for statement in statements:
        # Split each statement into key-value pairs based on the semi-colon
        if ';' in statement:
            key, value = statement.split(';', 1)  # Split only on the first occurrence# Remove any leading/trailing whitespace
            key = key.strip()
            value = value.strip()
            # Append the dictionary to the list
            result_dict[key] = value

    # Convert the flashcards into a DataFrame
    df = pd.DataFrame(list(result_dict.items()), columns=['Question', 'Answer'])
    return df
    
def get_csv(df):
    st.write(df)
    # Convert the DataFrame into a CSV file
    csv = df.to_csv(index=False)
    return csv

def create_anki_deck(df, deck_name, output_file):
    # Create a model for the cards
    my_model = genanki.Model(
        1607392319,
        'Simple Model',
        fields=[
            {'name': 'Question'},
            {'name': 'Answer'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': '{{Question}}',
                'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
            },
        ])

    # Create a deck
    my_deck = genanki.Deck(
        2059400110,
        deck_name)

    # Add notes (cards) to the deck
    for index, row in df.iterrows():
        note = genanki.Note(
            model=my_model,
            fields=[row['Question'], row['Answer']]
        )
        my_deck.add_note(note)

    output = io.BytesIO()
    genanki.Package(my_deck).write_to_file(output)
    output.seek(0)  # Reset the stream position to the beginning
    return output
    
st.set_page_config(page_title="Studyly | Study Smarter", layout="centered")

# Main Page
st.title("Studyly | Study Smarter With AI")
st.subheader("Upload a PDF of your notes. AI will generate flashcards that can download these as apkg (to upload to Anki) or csv")

# File upload
uploaded_notes = st.file_uploader("Upload Notes", type=["pdf"])

# When notes are uploaded
if uploaded_notes is not None:
    path = uploaded_notes.read()
    # Feed the notes into AI, have it generate CSV of flashcards, convert those to apkg
    with st.expander("See uploaded notes"):
        see_notes(path)
    try:
        ocr_box = st.checkbox("Enable OCR (do this if your notes are NOT typed)")
        if ocr_box:
            convert_button = st.button("Convert handwritten into flashcards", type="primary")
            if convert_button:
                with st.spinner("Generating flashcards... (may take a minute)"):
                    all_text = get_txt(path)
                    flashcard_str = generate_flashcards(all_text)
                    flashcard_df = get_df(flashcard_str)
                    st.download_button(label = "Download flashcards as CSV",
                                        data = get_csv(flashcard_df),
                                        file_name = "flashcards.csv",
                                        mime = "text/csv")
                    st.download_button(label = "Download flashcards as Anki Deck (APKG)",
                                        data = create_anki_deck(flashcard_df, "Studyly Flashcards", "studyly_flashcards.apkg"),
                                        file_name = "flashcards.apkg",
                                        mime = "application/apkg")
                # st.image(new_images)
                #st.write(ocr_text(uploaded_notes.read()))
                # image = Image.open(new_images)
                
                # reader = easyocr.Reader(["en"])
                # new_images_array = np.array(new_images)
                # result = reader.readtext(new_images_array)
                # st.write(result)
            
        else:
            convert_button = st.button("Convert typed into flashcards", type="primary")
            if convert_button:
                converted_text = digital_text(uploaded_notes)
                with st.spinner("Generating flashcards... (may take a minute)"):
                    flashcard_str = generate_flashcards(converted_text)    
                    # st.write(flashcard_str)
                    flashcard_df = get_df(flashcard_str)
                    st.download_button(label = "Download flashcards as CSV",
                                       data = get_csv(flashcard_df),
                                       file_name = "flashcards.csv",
                                       mime = "text/csv")
                    st.download_button(label = "Download flashcards as Anki Deck (APKG)",
                                       data = create_anki_deck(flashcard_df, "Studyly Flashcards", "studyly_flashcards.apkg"),
                                       file_name = "flashcards.apkg",
                                       mime = "application/apkg")
    except Exception as e:
        st.write(e)
