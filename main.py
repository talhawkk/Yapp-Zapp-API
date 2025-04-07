from flask import Flask, request, send_file, jsonify
import speech_recognition as sr
from gtts import gTTS
import google.generativeai as genai
import os
from dotenv import load_dotenv
import uuid

# Setup
app = Flask(__name__)
load_dotenv()
GOOGLE_GEMINI_API_KEY = os.getenv("GENAI_API_KEY")
genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

TOY_NAME = "Your Friend"
PERSONALITY = "a super fun, playful, friendly"

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
    prompt = f"You are {TOY_NAME}, a {PERSONALITY} AI toy. Reply in {lang_label} in a long, fun, and natural way. Input: {user_input}"
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API error: {e}")
        return "Oops, something went wrong!"

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
    temp_audio_path = f"temp_{uuid.uuid4().hex}.wav"
    file.save(temp_audio_path)

    user_text = audio_to_text(temp_audio_path)
    os.remove(temp_audio_path)

    if not user_text:
        return jsonify({'error': 'Could not understand audio'}), 400

    lang_code = detect_language(user_text)
    response_text = generate_response(user_text, lang_code)
    audio_response_path = text_to_speech(response_text, lang_code)

    return send_file(audio_response_path, mimetype="audio/mpeg", as_attachment=False)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
