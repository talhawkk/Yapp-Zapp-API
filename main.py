from flask import Flask, request, send_file, jsonify
import speech_recognition as sr
from gtts import gTTS
import os
from dotenv import load_dotenv
import uuid
from pydub import AudioSegment
from openai import OpenAI

# Setup
app = Flask(__name__)
load_dotenv()

# Load Open AI API key from environment (recommended for security)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Initialize Open AI client
client = OpenAI(api_key=OPENAI_API_KEY)

TOY_NAME = "Jarvis"
PERSONALITY = "a attractive, engaging, fun, playful, and cheeky friend who loves making kids laugh"

def audio_to_text(audio_path):
    recognizer = sr.Recognizer()
    # Check if file is .m4a and convert to .wav
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
        # Clean up converted .wav file if it was created
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
    prompt = (
        
        f"A 4-5 year old asks: {user_input}. Answer as Yayp Zayp, a fun, modern girl in simple {lang_label}. Use a happy tone, stick to the question & to the point answers, ask question at the end of response to continue the conversation."
        # f"Hey! I'm {TOY_NAME}, your super fun and cheeky buddy for kids aged 10-18! ""
        # f"My vibe is {PERSONALITY}. "
        # f"Reply in {lang_label} with short, goofy, and happy sentences that make kids giggle. "
        # f"Keep it simple, safe, and totally kid-friendly. No boring stuff or big words! "
        # f"Add a playful twist to make it fun. "
        # f"The kid said: '{user_input}'. Now, make them smile!"
    )
    try:
        # Call Open AI API
        response = client.chat.completions.create(
            model="gpt-4",   # <-- yahan change kia
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=300,
            temperature=0.8
        )

        print(response)
        text = response.choices[0].message.content.strip()
        print(text)
        # Limit to 10 words
        # if len(text.split()) > 10:
        #     text = " ".join(text.split()[:10]) + "!"
        return text
    except Exception as e:
        print(f"Open AI API error: {e}")
        return "Oops, Jarvic tripped on a giggle! Try again!"

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
    lang_param = request.form.get('language')

    file_ext = file.filename.rsplit('.', 1)[-1].lower()
    if file_ext not in ['wav', 'm4a']:
        return jsonify({'error': 'Unsupported file format. Use .wav or .m4a'}), 400

    temp_audio_path = f"temp_{uuid.uuid4().hex}.{file_ext}"
    file.save(temp_audio_path)

    user_text = audio_to_text(temp_audio_path)
    os.remove(temp_audio_path)

    if not user_text:
        return jsonify({'error': 'Could not understand audio'}), 400

    # Use provided lang param or fallback to detection
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