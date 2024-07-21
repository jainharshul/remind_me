# Importing required libraries
from pydub import AudioSegment
import speech_recognition as sr
import spacy
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import re

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
    # Improved regex pattern to match various date and time formats
    date_pattern = re.compile(r'(\w+ \d{1,2}(?:st|nd|rd|th)?)\s+at\s+(\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.))')
    match = date_pattern.search(text)

    if match:
        date_str = match.group(1)
        time_str = match.group(2)

        print(f"Matched Date String: {date_str}")
        print(f"Matched Time String: {time_str}")

        # Remove suffixes like 'st', 'nd', 'rd', 'th'
        date_str = re.sub(r'(st|nd|rd|th)', '', date_str).strip()

        # Normalize the time string
        time_str = time_str.replace('a.m.', 'AM').replace('p.m.', 'PM')

        # Combine date and time strings
        date_time_str = f"{date_str} {time_str}"

        print(f"Combined Date Time String: {date_time_str}")

        try:
            # Parse date and time using the corrected format
            date = datetime.strptime(date_time_str, '%B %d %I:%M %p')
            # Set the date to the current year if needed
            date = date.replace(year=datetime.now().year)
            # Convert to ISO 8601 format
            date_iso = date.isoformat()
        except ValueError as e:
            print(f"Date parsing error: {e}")
            date_iso = None

        # Extract the reminder text
        reminder = text.split(match.group(0), 1)[-1].strip()
    else:
        date_iso = None
        reminder = text
    
    return date_iso, reminder

# Function to add event to Google Calendar
def add_event_to_calendar(date, reminder):
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = 'erm.json'
    
    # Debugging output
    print("Adding event to calendar with:")
    print(f"Date: {date}")
    print(f"Reminder: {reminder}")
    
    if not date or not reminder:
        print("Invalid date or reminder. Cannot create event.")
        return
    
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
    
    # Debugging output
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

        print("Event data:")
        print(event)
        
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {created_event.get('htmlLink')}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Function to list events from Google Calendar
def list_events():
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    SERVICE_ACCOUNT_FILE = 'erm.json'
    
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
    
    # List events for the next 30 days
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(f"{start} - {event.get('summary')}")

# Main function to run the script
def main(mp3_file):
    wav_file = "output.wav"
    convert_mp3_to_wav(mp3_file, wav_file)
    
    transcription = transcribe_audio(wav_file)
    print(f"Transcription: {transcription}")
    
    date, reminder = extract_date_and_reminder(transcription)
    print(f"Extracted Date: {date}")
    print(f"Extracted Reminder: {reminder}")
    
    add_event_to_calendar(date, reminder)
    print("Listing events to verify:")
    list_events()

# Run the main function
if __name__ == "__main__":
    main("test.mp3")
