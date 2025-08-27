import requests
from bs4 import BeautifulSoup
import os
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cooldown_time = int(os.getenv("COOLDOWN_TIME", 60))

profiles_to_watch = os.getenv("PROFILES", "").split(",") if os.getenv("PROFILES") else []
steam_profile_url = 'https://steamcommunity.com/id/{profile}/'
playing_profiles = {}

# Load cookies from file
def load_cookies():
    """Load cookies from cookies.txt file in Netscape HTTP Cookie File format"""
    cookies = {}
    try:
        with open('cookies.txt', 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#') and not line.startswith('Netscape'):
                    # Parse Netscape cookie format
                    # domain flag path secure expiration name value
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        cookie_name = parts[5]
                        cookie_value = parts[6]
                        cookies[cookie_name] = cookie_value
    except FileNotFoundError:
        logger.warning("cookies.txt file not found. Continuing without cookies.")
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
    return cookies

# Realistic headers to mimic a real browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0'
}

class SteamKind:
    PLAYING = "Currently In-Game"
    NOT_PLAYING = "Not Playing"

def send_to_webhook(data):
    """Send data to the webhook service"""
    try:
        r = requests.post(
            "http://webhook-service:8000/steam/profiles",
            json=data,
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        print(f"Error sending to webhook: {e}")

def get_playing_profiles(profiles_to_watch) -> dict:
    # Load cookies each time in case they change
    cookies = load_cookies()
    
    for profile in profiles_to_watch:
        game = None
        status = SteamKind.NOT_PLAYING
        
        try:
            response = requests.get(
                steam_profile_url.format(profile=profile),
                headers=HEADERS,
                cookies=cookies
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')

            profile_element = soup.find("div", class_="profile_in_game_header")
            game_element = soup.find("div", class_="profile_in_game_name")
            
            if profile_element and SteamKind.PLAYING in profile_element.get_text(strip=True):
                status = SteamKind.PLAYING
                if game_element:
                    game = game_element.get_text(strip=True)

            if playing_profiles.get(profile, {}).get("status") != status and status == SteamKind.PLAYING:
                send_to_webhook({
                    "profile": profile,
                    "status": status,
                    "game": game,
                })

            playing_profiles[profile] = {
                "status": status,
                "game": game,
            }
        except Exception as e:
            logger.error(f"Error fetching profile {profile}: {e}")
            playing_profiles[profile] = {
                "status": "Error",
                "game": None,
                "error": str(e)
            }
    
    time.sleep(cooldown_time)
    return playing_profiles


def main():
    while True:
        profiles = get_playing_profiles(profiles_to_watch)
    

if __name__ == "__main__":
    main()

