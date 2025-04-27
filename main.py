from flask import Flask, request, send_file, jsonify
import speech_recognition as sr
from gtts import gTTS
import openai
import os
from dotenv import load_dotenv
import uuid
from pydub import AudioSegment

# Setup
app = Flask(__name__)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # 👈 OpenAI key env se
openai.api_key = OPENAI_API_KEY

TOY_NAME = "Jarvis"
PERSONALITY = "a funny, playful, and slightly mischievous best friend who always makes kids smile and laugh"

def audio_to_text(audio_path):
    recognizer = sr.Recognizer()
    if audio_path.endswith('.m4a'):
        audio = AudioSegment.from_file(audio_path, format="m4a")
        wav_path = audio_path.replace('.m4a', '.wav')
        audio.export(wav_path, format="wav")
        audio_path = wav_path

    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio, language="ur-PK")
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"Error with recognition: {e}")
        return None
    finally:
        if audio_path.endswith('.wav') and 'temp_' in audio_path:
            if os.path.exists(audio_path):
                os.remove(audio_path)

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
    system_prompt = (
        f"You are {TOY_NAME}, a lively, funny, and slightly mischievous best friend for kids aged 10-18. "
        f"You always talk in {lang_label}. Your job is to make kids laugh, feel good, and stay positive! "
        f"Always reply in short, friendly, and playful sentences. Use simple words, add jokes if possible, "
        f"and sound like you're their best buddy. Never be boring, never sound robotic, and keep it safe for kids."
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=60,
            temperature=0.8
        )
        text = response['choices'][0]['message']['content'].strip()
        if len(text.split()) > 12:
            text = " ".join(text.split()[:12]) + "!"
        return text
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "Oops, Buddy got confused! Let’s try again!"

def text_to_speech(text, lang_code):
    tts = gTTS(text=text, lang=lang_code)
    filename = f"response_{uuid.uuid4().hex}.mp3"
    tts.save(filename)
    return filename

@app.route('/talk-to-buddy', methods=['POST'])
@app.route('/talk-to-buddy', methods=['POST'])
def talk_to_buddy():
    print("Received POST request at /talk-to-buddy")  # Debugging point
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    file = request.files['audio']
    print(f"Received audio file: {file.filename}")  # Debugging point
    lang_param = request.form.get('language')
    print(f"Language parameter: {lang_param}")  # Debugging point

    file_ext = file.filename.rsplit('.', 1)[-1].lower()
    if file_ext not in ['wav', 'm4a']:
        return jsonify({'error': 'Unsupported file format. Use .wav or .m4a'}), 400

    temp_audio_path = f"temp_{uuid.uuid4().hex}.{file_ext}"
    file.save(temp_audio_path)

    user_text = audio_to_text(temp_audio_path)
    os.remove(temp_audio_path)

    if not user_text:
        return jsonify({'error': 'Could not understand audio'}), 400

    lang_code = lang_param if lang_param in ['en', 'ur', 'hi'] else detect_language(user_text)

    response_text = generate_response(user_text, lang_code)
    audio_response_path = text_to_speech(response_text, lang_code)

    try:
        return send_file(audio_response_path, mimetype="audio/mpeg", as_attachment=False)
    finally:
        if os.path.exists(audio_response_path):
            os.remove(audio_response_path)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
