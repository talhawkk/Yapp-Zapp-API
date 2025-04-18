from flask import Flask, request, send_file, jsonify
import speech_recognition as sr
from gtts import gTTS
import google.generativeai as genai
import os
from dotenv import load_dotenv
import uuid

import subprocess

def convert_m4a_to_wav(m4a_path):
    wav_path = f"{uuid.uuid4().hex}.wav"
    try:
        subprocess.run(['ffmpeg', '-i', m4a_path, wav_path], check=True)
        return wav_path
    except subprocess.CalledProcessError as e:
        print("FFmpeg conversion error:", e)
        return None

# Setup
app = Flask(__name__)
load_dotenv()
GOOGLE_GEMINI_API_KEY = os.getenv("GENAI_API_KEY")
genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

TOY_NAME = "Jarvic"
PERSONALITY = "a super fun, playful, and cheeky friend who loves making kids laugh"

def audio_to_text(audio_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio, language="ur-PK")
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"Error with recognition: {e}")
        return None

def detect_language(text):
    urdu_chars = set("ءآأؤإئبتثجحخدذرزسشصضطظعغفقكلمنهوىي")
    hindi_chars = set("अआइईउऊएऐओऔऋकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह")
    if any(char in urdu_chars for char in text):
        return "ur"
    elif any(char in hindi_chars for char in text):
        return "hi"
    else:
        return "en"

def generate_response(user_input, lang_code):
    lang_label = {"en": "English", "ur": "Urdu", "hi": "Hindi"}[lang_code]
    prompt = (
        f"You are {TOY_NAME}, a cheerful and playful AI toy designed for kids aged 10-18. "
        f"Your personality is {PERSONALITY}. "
        f"Always respond in {lang_label} with short, simple, and fun sentences that make kids laugh or feel happy. "
        f"Keep it safe, friendly, and appropriate for children. "
        f"Don’t use big words or complicated ideas. "
        f"dont bore the users"
        f"User said: '{user_input}'"
    )
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Response ko 10 words tak limit karo
        if len(text.split()) > 10:
            text = " ".join(text.split()[:10]) + "!"
        return text
    except Exception as e:
        print(f"Gemini API error: {e}")
        return "Oops, Buddy got confused! Let’s try again!"

def text_to_speech(text, lang_code):
    tts = gTTS(text=text, lang=lang_code)
    filename = f"response_{uuid.uuid4().hex}.mp3"
    tts.save(filename)
    return filename

@app.route('/talk-to-buddy', methods=['POST'])
def talk_to_buddy():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    file = request.files['audio']
    original_audio_path = f"temp_{uuid.uuid4().hex}.m4a"
    file.save(original_audio_path)

    # Convert to .wav using FFmpeg
    converted_audio_path = convert_m4a_to_wav(original_audio_path)
    os.remove(original_audio_path)

    if not converted_audio_path:
        return jsonify({'error': 'Audio conversion failed'}), 500

    user_text = audio_to_text(converted_audio_path)
    os.remove(converted_audio_path)

    if not user_text:
        return jsonify({'error': 'Could not understand audio'}), 400

    lang_code = detect_language(user_text)
    response_text = generate_response(user_text, lang_code)
    audio_response_path = text_to_speech(response_text, lang_code)

    try:
        return send_file(audio_response_path, mimetype="audio/mpeg", as_attachment=False)
    finally:
        if os.path.exists(audio_response_path):
            os.remove(audio_response_path)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))