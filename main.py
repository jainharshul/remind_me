# Importing required libraries
from pydub import AudioSegment
import speech_recognition as sr
import spacy
from google.oauth2 import service_account
from googleapiclient.discovery import build

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

# Load the spaCy model for NLP
nlp = spacy.load("en_core_web_sm")

# Function to extract date and reminder from text
def extract_date_and_reminder(text):
    doc = nlp(text)
    date = None
    reminder = None
    for ent in doc.ents:
        if ent.label_ == "DATE" or ent.label_ == "TIME":
            date = ent.text
        elif ent.label_ == "MISC":
            reminder = ent.text
    return date, reminder

# Function to add event to Google Calendar
def add_event_to_calendar(date, reminder):
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = 'path/to/your-service-account-file.json'
    
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
    
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
    
    event = service.events().insert(calendarId='primary', body=event).execute()
    print(f"Event created: {event.get('htmlLink')}")

# Main function to run the script
def main(mp3_file):
    wav_file = "output.wav"
    convert_mp3_to_wav(mp3_file, wav_file)
    
    transcription = transcribe_audio(wav_file)
    print(f"Transcription: {transcription}")
    
    date, reminder = extract_date_and_reminder(transcription)
    if date and reminder:
        add_event_to_calendar(date, reminder)
    else:
        print("Could not extract date and reminder from the transcription.")

# Run the main function
if __name__ == "__main__":
    main("your-audio-file.mp3")
