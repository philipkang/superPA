import os
import tempfile
import whisper
from pydub import AudioSegment
import openai
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, VideoUnavailable
import PyPDF2
import docx
import io

# Load Whisper model
model = whisper.load_model("base")

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Ensure /temp directory exists
temp_dir = os.path.join(os.getcwd(), "temp")
os.makedirs(temp_dir, exist_ok=True)

# Initialize session state
if 'youtube_url' not in st.session_state:
    st.session_state.youtube_url = ""
if 'input_key' not in st.session_state:
    st.session_state.input_key = 0
if 'content' not in st.session_state:
    st.session_state.content = ""
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'question_key' not in st.session_state:
    st.session_state.question_key = 0
if 'summary' not in st.session_state:
    st.session_state.summary = ""

def reset_app():
    st.session_state.youtube_url = ""
    st.session_state.input_key += 1
    st.session_state.content = ""
    st.session_state.chat_history = []
    st.session_state.question_key += 1
    st.session_state.summary = ""

def transcribe_audio(audio_file_path):
    result = model.transcribe(audio_file_path)
    return result['text']

def summarize_text(text):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Use the correct model name
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Summarize the following text:\n\n{text}"}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred while summarizing the text: {e}")
        return None

def process_video(video_file):
    with tempfile.NamedTemporaryFile(suffix=".wav", dir=temp_dir, delete=False) as temp_audio_file:
        video_audio = AudioSegment.from_file(video_file, format="mp4")
        video_audio.export(temp_audio_file.name, format="wav")
        temp_audio_file.close()
        transcript = transcribe_audio(temp_audio_file.name)
        os.remove(temp_audio_file.name)
        return transcript

def process_audio(audio_file):
    audio = AudioSegment.from_file(audio_file)
    with tempfile.NamedTemporaryFile(suffix=".wav", dir=temp_dir, delete=False) as temp_audio_file:
        audio.export(temp_audio_file.name, format="wav")
        temp_audio_file.close()
        transcript = transcribe_audio(temp_audio_file.name)
        os.remove(temp_audio_file.name)
        return transcript

def process_youtube_video(url):
    try:
        video_id = url.split("v=")[-1]
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([item['text'] for item in transcript_list])
        return transcript
    except NoTranscriptFound:
        st.error("No transcript found for this video.")
        return None
    except VideoUnavailable:
        st.error("Video is unavailable.")
        return None
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

def process_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def process_docx(docx_file):
    doc = docx.Document(docx_file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def process_txt(txt_file):
    return txt_file.getvalue().decode("utf-8")

def get_ai_response(question, context):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Use the correct model name
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Answer questions based only on the provided context. If the question is not related to the context, respond with 'Please ask a question related to the media content.'"},
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"}
            ],
            max_tokens=700
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred while getting AI response: {e}")
        return None

# Streamlit interface
st.title("Document Summarizer and Q&A")

# Reset button (red color)
if st.button('Reset', type="primary", key="reset_button"):
    reset_app()

# Handle file upload
uploaded_file = st.file_uploader("Upload a file (video, audio, PDF, DOCX, or TXT)", type=["mp4", "mp3", "wav", "pdf", "docx", "txt"])

if uploaded_file is not None and not st.session_state.content:
    file_type = uploaded_file.name.split(".")[-1].lower()
    
    if file_type == "mp4":
        with st.spinner("Processing video..."):
            transcript = process_video(uploaded_file)
    elif file_type in ["mp3", "wav"]:
        with st.spinner("Processing audio..."):
            transcript = process_audio(uploaded_file)
    elif file_type == "pdf":
        with st.spinner("Processing PDF..."):
            transcript = process_pdf(uploaded_file)
    elif file_type == "docx":
        with st.spinner("Processing DOCX..."):
            transcript = process_docx(uploaded_file)
    elif file_type == "txt":
        with st.spinner("Processing TXT..."):
            transcript = process_txt(uploaded_file)
    
    if transcript:
        st.session_state.content = transcript
        with st.spinner("Summarizing..."):
            st.session_state.summary = summarize_text(transcript)

if st.session_state.summary:
    st.write("**Summary:**")
    st.write(st.session_state.summary)

# Handle YouTube video URL
youtube_url = st.text_input("Enter YouTube video URL to summarize", key=f"youtube_url_input_{st.session_state.input_key}")

if youtube_url and youtube_url != st.session_state.youtube_url:
    with st.spinner("Processing YouTube video..."):
        transcript = process_youtube_video(youtube_url)
        
    if transcript:
        st.session_state.content = transcript
        st.session_state.youtube_url = youtube_url
        with st.spinner("Summarizing..."):
            st.session_state.summary = summarize_text(transcript)
            st.write("**Summary:**")
            st.write(st.session_state.summary)

# Chat interface
st.write("**Ask questions about the content:**")
user_question = st.text_input("Your question:", key=f"user_question_{st.session_state.question_key}")

if user_question:
    if st.session_state.content:
        ai_response = get_ai_response(user_question, st.session_state.content)
        st.session_state.chat_history.append(("You", user_question))
        st.session_state.chat_history.append(("AI", ai_response))
    else:
        ai_response = "Please upload a file or enter a YouTube URL first."
        st.session_state.chat_history.append(("AI", ai_response))

# Display chat history
for role, message in st.session_state.chat_history:
    if role == "You":
        st.write(f"**You:** {message}")
    else:
        st.write(f"**AI:** {message}")