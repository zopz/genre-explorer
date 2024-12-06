"""
Genre bot is meant to be run on a regular cron schedule.
It will pull a random subgenre from musicmap.info and post its info to Slack
"""
import os
import json
import random
from datetime import datetime
from io import StringIO
from html.parser import HTMLParser
import requests
from dotenv import load_dotenv
from requests.exceptions import HTTPError

load_dotenv()

SOURCE_URL = 'https://musicmap.info/master-genrelist.json'
SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']

# They don't like python UA over there
headers = {'User-Agent': ''}

class MLStripper(HTMLParser):
    """
    Strip html tags from input and return a sanitized string
    """
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = StringIO()
    def handle_data(self, data):
        """
        handle input data
        """
        self.text.write(data)
    def get_data(self):
        """
        get data
        """
        return self.text.getvalue()

def strip_tags(html):
    """
    Call mlstripper class to sanitize html out of input string
    """
    strip = MLStripper()
    strip.feed(html)
    return strip.get_data()

def get_genre_list():
    """
    Send the request to the API to get the genre list
    """
    try:
        response = requests.get(SOURCE_URL, headers=headers, timeout=30)
        response.raise_for_status()
        json_response = response.json()

    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')

    return json_response

def genre_was_sent(genre_name):
    """
    Check the data backend if a genre was already posted, and if so return true
    """
    try:
        with open("genres.txt", "r", encoding="utf8") as file:
            previous = file.read()
        if genre_name in previous:
            return True
    except FileNotFoundError:
        with open("genres.txt", "x", encoding="utf8") as file:
            file.write("")

    return False

def update_sent_genre_list(genre_name):
    """
    Add a genre to the sent genre file 
    """
    with open("genres.txt", "a", encoding="utf8") as file:
        file.write(f"{genre_name}\n")

def get_current_day():
    """
    Get current date and return a human-readable day name
    """
    current_date = datetime.now()
    day_name = current_date.strftime('%A')
    return day_name

def get_random_genre(json_response):
    """
    Take in API responses data and pull a random subgenre. If it has been used already,
    or if it is a supergenre, pull another one.
    """
    genre_data = {'name': 'notarealgenre', 'supergenre': 'true'}
    # We do not want supergenres, only subgenres
    while "supergenre" in genre_data or genre_was_sent(genre_data['name']):
        genre_data = random.choice(list(json_response.values()))
    return genre_data

def send_slack_message(genre_data):
    """
    Parse genre data and send the formatted message to slack
    """
    name = strip_tags(genre_data['name'])
    description = strip_tags(genre_data['description'])
    youtube_link = strip_tags(genre_data['playlist-link'])
    spotify_link = strip_tags(genre_data['spotify-playlist-link'])
    message_data = {
        'attachments': [
            {
                'fallback': f"Genre of the day is {name}",
                'blocks': [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*It's {get_current_day()}, dig somethin' different!*" \
                                f"\n:musical_note: _{name}_ :musical_note:" \
                                f"\n<{youtube_link}|Youtube Playlist>" \
                                f"\n<{spotify_link}|Spotify Playlist>"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Description*\n```\n{description}\n```"
                        }
                    }
                ]
            }
        ]
    }
    json_data = json.dumps(message_data)
    requests.post(SLACK_WEBHOOK_URL, data=json_data, timeout=30)
    update_sent_genre_list(name)

def main():
    """
    Call main function
    """
    json_response = get_genre_list()
    genre_data = get_random_genre(json_response)
    send_slack_message(genre_data)

main()
