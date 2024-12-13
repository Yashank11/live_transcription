import streamlit as st
# Set page config first, before any other Streamlit commands
st.set_page_config(
    page_title="Smart Transcription Assistant",
    page_icon="🎤",
    layout="wide"
)

import assemblyai as aai
from typing import Optional
import time
import queue
import threading
from datetime import datetime
import json
import os
from pathlib import Path
from groq import Groq

# Set API keys
aai.settings.api_key = "644ddd7f18fb411695a69d69b8c8ecf6"
groq_client = Groq(api_key="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")

# Custom CSS for better UI
st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
        height: 50px;
        font-size: 18px;
    }
    .transcript-box {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 20px;
        margin: 10px 0;
        background-color: #f8f9fa;
    }
    .status-box {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .recording {
        background-color: #ffebee;
        border: 1px solid #ffcdd2;
    }
    </style>

    <script>
    let mediaRecorder;
    let socket;
    let isRecording = false;
    
    const startRecording = async () => {
        if (isRecording) return;
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm',
                audioBitsPerSecond: 128000
            });
            
            // Connect to AssemblyAI websocket
            socket = new WebSocket('wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000');
            
            socket.onopen = () => {
                socket.send(JSON.stringify({
                    'token': '644ddd7f18fb411695a69d69b8c8ecf6',
                    'sample_rate': 16000
                }));
                
                mediaRecorder.start(250); // Send audio data every 250ms
                isRecording = true;
            };
            
            socket.onmessage = (message) => {
                const response = JSON.parse(message.data);
                if (response.message_type === 'FinalTranscript' || response.message_type === 'PartialTranscript') {
                    window.parent.postMessage({
                        type: 'transcription',
                        data: response.text,
                        isFinal: response.message_type === 'FinalTranscript'
                    }, '*');
                }
            };
            
            mediaRecorder.addEventListener('dataavailable', async (event) => {
                if (event.data.size > 0 && socket.readyState === 1) {
                    // Convert audio data to the correct format and send to AssemblyAI
                    const reader = new FileReader();
                    reader.onload = () => {
                        const buffer = reader.result;
                        socket.send(JSON.stringify({
                            'audio_data': btoa(buffer)
                        }));
                    };
                    reader.readAsBinaryString(event.data);
                }
            });
            
        } catch (err) {
            console.error("Error accessing microphone:", err);
            alert("Error accessing microphone. Please ensure microphone permissions are granted.");
        }
    };
    
    const stopRecording = () => {
        if (!isRecording) return;
        
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            
            if (socket) {
                socket.close();
            }
            
            isRecording = false;
        }
    };
    </script>
    """, unsafe_allow_html=True)

class TranscriptionApp:
    def __init__(self):
        self.transcript_queue = queue.Queue()
        self.is_transcribing = False
        self.current_transcript = ""
        self.full_transcript = []
        self.session_start_time = None
        
    def save_transcript(self):
        if not self.full_transcript:
            return
            
        Path("transcripts").mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcripts/transcript_{timestamp}.json"
        
        transcript_data = {
            "timestamp": datetime.now().isoformat(),
            "transcript": self.full_transcript
        }
        
        with open(filename, "w") as f:
            json.dump(transcript_data, f, indent=2)
        
        st.success(f"Transcript saved to {filename}")
    
    def summarize_transcript(self):
        if not self.full_transcript:
            return "No transcript available to summarize."
            
        full_text = " ".join(self.full_transcript)
        
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates concise summaries."
                    },
                    {
                        "role": "user",
                        "content": f"Please provide a concise summary of the following transcript: {full_text}"
                    }
                ],
                model="mixtral-8x7b-32768",
                temperature=0.5,
                max_tokens=150
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error generating summary: {str(e)}"

def main():
    # Initialize session state
    if 'app' not in st.session_state:
        st.session_state.app = TranscriptionApp()
    
    # Sidebar with company logo and information
    with st.sidebar:
        # Add a company logo
        st.image("OLC.jpeg", use_column_width=True, caption="Vinnovate Technologies")
        
        # Add company information
        st.markdown("""
            ### About Us
            **Smart Transcription Assistant** is a product of **Vinnovate Technologies**, committed to delivering cutting-edge transcription and summarization tools powered by advanced AI technologies.
            
            🌐 Visit us: [https://www.vinnovatetechnologies.com/](https://www.vinnovatetechnologies.com/)  
            📧 Contact us: contact@vinnovatetechnologies.com  
        """)
    
    # Header with custom styling
    st.markdown("""
        <h1 style='text-align: center; color: #1E88E5;'>
            🎤 Smart Transcription Assistant
        </h1>
    """, unsafe_allow_html=True)
    
    # Control Panel
    with st.container():
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("🎙️ Start Recording", 
                        type="primary",
                        key="start_button",
                        on_click=lambda: st.session_state.update(is_recording=True)):
                st.markdown("<script>startRecording();</script>", unsafe_allow_html=True)
        
        with col2:
            if st.button("⏹️ Stop Recording",
                        type="secondary",
                        key="stop_button",
                        on_click=lambda: st.session_state.update(is_recording=False)):
                st.markdown("<script>stopRecording();</script>", unsafe_allow_html=True)
        
        with col3:
            if st.button("📝 Summarize Transcript",
                        disabled=not st.session_state.app.full_transcript):
                summary = st.session_state.app.summarize_transcript()
                st.session_state['summary'] = summary
    
    # Status Indicator
    if st.session_state.get('is_recording', False):
        st.markdown("""
            <div class='status-box recording'>
                🔴 Recording in progress...
            </div>
        """, unsafe_allow_html=True)
    
    # Live Transcription Display
    with st.container():
        st.subheader("Live Transcription")
        transcript_placeholder = st.empty()
    
    # Transcript History
    with st.container():
        st.subheader("Transcript History")
        transcript_history = st.empty()
    
    # Summary Display
    if 'summary' in st.session_state:
        with st.container():
            st.subheader("Summary")
            st.markdown(f"*{st.session_state['summary']}*")
    
    # Handle incoming transcriptions
    st.markdown("""
        <script>
        window.addEventListener('message', function(event) {
            if (event.data.type === 'transcription') {
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    data: {
                        text: event.data.data,
                        isFinal: event.data.isFinal
                    }
                }, '*');
            }
        });
        </script>
    """, unsafe_allow_html=True)
    
    # Process transcription updates
    if 'transcription' not in st.session_state:
        st.session_state.transcription = {'text': '', 'isFinal': False}
    
    if st.session_state.transcription.get('isFinal', False):
        st.session_state.app.full_transcript.append(st.session_state.transcription['text'])
        transcript_history.markdown("\n\n".join(
            [f"🔹 {t}" for t in st.session_state.app.full_transcript]
        ))
        st.session_state.transcription = {'text': '', 'isFinal': False}
    else:
        transcript_placeholder.markdown(f"*Transcribing: {st.session_state.transcription.get('text', '')}*")

    # Add Footer
    st.markdown("""
        <style>
            .footer {
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                background-color: #000000;
                padding: 10px 0;
                text-align: center;
                font-size: 14px;
                color: #6c757d;
            }
            .footer a {
                color: #1E88E5;
                text-decoration: none;
            }
            .footer a:hover {
                text-decoration: underline;
            }
        </style>
        <div class="footer">
            © 2024 Vinnovate Technologies. All rights reserved.  
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()