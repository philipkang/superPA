import os
import tempfile
import whisper
from pydub import AudioSegment
import openai
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, VideoUnavailable

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

def reset_app():
    st.session_state.youtube_url = ""
    st.session_state.input_key += 1

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

# Streamlit interface
st.title("Video/Audio/YouTube Summarizer")

# Reset button (red color)
if st.button('Reset', type="primary", key="reset_button"):
    reset_app()

# Handle file upload
uploaded_file = st.file_uploader("Upload a video (mp4) or audio (mp3/wav) file", type=["mp4", "mp3", "wav"])

if uploaded_file is not None:
    file_type = uploaded_file.name.split(".")[-1]
    
    if file_type == "mp4":
        with st.spinner("Processing video..."):
            transcript = process_video(uploaded_file)
    elif file_type in ["mp3", "wav"]:
        with st.spinner("Processing audio..."):
            transcript = process_audio(uploaded_file)
    
    if transcript:
        with st.spinner("Summarizing..."):
            summary = summarize_text(transcript)
            st.write("**Summary:**")
            st.write(summary)

# Handle YouTube video URL
youtube_url = st.text_input("Enter YouTube video URL to summarize", key=f"youtube_url_input_{st.session_state.input_key}")

if youtube_url:
    with st.spinner("Processing YouTube video..."):
        transcript = process_youtube_video(youtube_url)
        
    if transcript:
        with st.spinner("Summarizing..."):
            summary = summarize_text(transcript)
            st.write("**Summary:**")
            st.write(summary)