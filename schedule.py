from __future__ import print_function
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
 
import datetime
import json
 
import os
 
 
CLIENT_SECRET_FILE = 'calender_key.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']
 
DATE_TIME_FORMAT = "%y-%m-%dT%H:%M:%S"
 
class google_calendar_api:
 
    def __init__(self):
        self.service = None
 
    def build_service(self):
        global CLIENT_SECRET_FILE
        global SCOPES
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(CLIENT_SECRET_FILE):
            creds = Credentials.from_authorized_user_file(CLIENT_SECRET_FILE, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(CLIENT_SECRET_FILE, 'w') as token:
                token.write(creds.to_json())
 
        try:
            self.service = build('calendar', 'v3', credentials=creds)
        except HttpError as err:
            print(err)
 
    def create_event(self, calendar_id, start, end, desc='', summary=''):
        #service = self.build_service()
        #self.build_service()
        event = self.service.events().insert(calendarId=calendar_id, body={
            'description': desc,
            'summary': summary,
            'start': {'dateTime': start, 'timeZone': 'Europe/Moscow'},
            'end': {'dateTime': end, 'timeZone': 'Europe/Moscow'},
        }).execute()
        return event['id']
 
    def update_event(self, calendar_id, event_id, desc='', summary='', start='', end=''):
        event = self.get_event(calendar_id, event_id)
        if summary != '':
            event["summary"] = summary
        if desc != '':
            event["description"] = desc
        if start != '':
            event["start"]['dateTime'] = start
        if end != '':
            event["end"]['dateTime'] = end
        updated_event = self.service.events().update(calendarId=calendar_id, eventId=event['id'], body=event).execute()
        return updated_event["id"]
 
    def get_event(self, calendar_id, event_id):
        return self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
 
    def get_events(self, calendar_id, start, last='', max_res=10):
        now = start + '+03:00'
        oth = dict()
        if last != '':
            oth["timeMax"] = last + '+03:00'
        event_results = self.service.events().list(calendarId=calendar_id,
                                                   timeMin=now, maxResults=max_res,
                                                   singleEvents=True,
                                                   orderBy='startTime', **oth).execute()
        res = event_results.get('items', [])
        return res
 
 
CALENDAR_ID = 'PRODUCTION-SECRET@group.calendar.google.com'
 
calendar_api = None
 
def setup():
    global calendar_api
    calendar_api = google_calendar_api()
    calendar_api.build_service()
 
 
def get_datetime(date: str, time: str):
    ar = date.split('.')
    ar.reverse()
    res = '-'.join(ar) + 'T' + time
    return res
 
 
def parse_datetime_str(dt: str):
    ar = dt.split('T')
    date = ar[0].split('-')
    date.reverse()
    date = '.'.join(date)
    return date, ar[1].split('+')[0]
 
 
if __name__ == '__main__':
    setup()
    calendar_api.get_events(CALENDAR_ID, "2023-03-12T17:30:00")
