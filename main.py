from flask import Flask, request, redirect, url_for, render_template
import os
from pydub import AudioSegment
import speech_recognition as sr
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timezone

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'mp3'}

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Function to convert MP3 to WAV
def convert_mp3_to_wav(mp3_file, wav_file):
    audio = AudioSegment.from_mp3(mp3_file)
    audio.export(wav_file, format="wav")

# Function to transcribe audio from WAV file
def transcribe_audio(wav_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_file) as source:
        audio = recognizer.record(source)
    return recognizer.recognize_google(audio)

# Function to extract date and reminder from text
def extract_date_and_reminder(text):
    date_pattern = re.compile(r'(\w+ \d{1,2}(?:st|nd|rd|th)?)\s+at\s+(\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.))')
    match = date_pattern.search(text)

    if match:
        date_str = match.group(1)
        time_str = match.group(2)

        date_str = re.sub(r'(st|nd|rd|th)', '', date_str).strip()
        time_str = time_str.replace('a.m.', 'AM').replace('p.m.', 'PM')

        date_time_str = f"{date_str} {time_str}"

        try:
            date = datetime.strptime(date_time_str, '%B %d %I:%M %p')
            date = date.replace(year=datetime.now().year)
            date_iso = date.isoformat()
        except ValueError as e:
            print(f"Date parsing error: {e}")
            date_iso = None

        reminder = text.split(match.group(0), 1)[-1].strip()
    else:
        date_iso = None
        reminder = text
    
    return date_iso, reminder

# Function to add event to Google Calendar
def add_event_to_calendar(date, reminder):
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = 'erm.json'
    
    if not date or not reminder:
        return
    
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
    
    try:
        event = {
            'summary': reminder,
            'start': {
                'dateTime': date,
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': date,
                'timeZone': 'America/Los_Angeles',
            },
        }

        created_event = service.events().insert(calendarId='primary', body=event).execute()
    except Exception as e:
        print(f"An error occurred: {e}")

# Function to list events from Google Calendar
def list_events():
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    SERVICE_ACCOUNT_FILE = 'erm.json'
    
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)

    now = datetime.now(timezone.utc).isoformat()
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])
    return events

# Function to delete an event from Google Calendar
def delete_event(event_id):
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = 'erm.json'
    
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)

    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
    except Exception as e:
        print(f"An error occurred while deleting the event: {e}")

@app.route('/', methods=['GET'])
def index():
    events = list_events()
    return render_template('index.html', events=events)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded.mp3')
        file.save(filename)
        
        wav_file = os.path.join(app.config['UPLOAD_FOLDER'], 'output.wav')
        convert_mp3_to_wav(filename, wav_file)
        
        transcription = transcribe_audio(wav_file)
        date, reminder = extract_date_and_reminder(transcription)
        
        add_event_to_calendar(date, reminder)
        
        return redirect(url_for('index'))
    
    return 'File type not allowed.'

@app.route('/delete/<event_id>', methods=['POST'])
def delete(event_id):
    delete_event(event_id)
    return redirect(url_for('index'))

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
