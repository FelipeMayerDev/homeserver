import requests
import os
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

active_check_interval = int(os.getenv("ACTIVE_CHECK_INTERVAL", 30))
offline_check_interval = int(os.getenv("OFFLINE_CHECK_INTERVAL", 300))
steam_api_key = os.getenv("STEAM_API_KEY")

profiles_to_watch = os.getenv("PROFILES", "").split(",") if os.getenv("PROFILES") else []
playing_profiles = {}

STEAM_API_BASE = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
COMMUNITY_RESOLVE_URL = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"

def resolve_vanity_url(vanity_url):
    """Resolve vanity URL to Steam64 ID"""
    if not steam_api_key:
        logger.error("STEAM_API_KEY not set")
        return None

    try:
        response = requests.get(
            COMMUNITY_RESOLVE_URL,
            params={"key": steam_api_key, "vanityurl": vanity_url}
        )
        response.raise_for_status()
        data = response.json()

        if data["response"]["success"] == 1:
            return data["response"]["steamid"]
        return None
    except Exception as e:
        logger.error(f"Error resolving vanity URL {vanity_url}: {e}")
        return None

def get_steam_id(profile):
    """Get Steam64 ID from profile (handles both vanity URLs and numeric IDs)"""
    profile = profile.strip()
    if profile.isdigit():
        return profile
    return resolve_vanity_url(profile)

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

class SteamKind:
    PLAYING = "Currently In-Game"
    NOT_PLAYING = "Not Playing"

def get_player_summaries_with_backoff(steam_ids, retry_count=0):
    """Get player summaries with exponential backoff for 429 errors"""
    if not steam_api_key:
        logger.error("STEAM_API_KEY not set")
        return {}

    try:
        response = requests.get(
            STEAM_API_BASE,
            params={"key": steam_api_key, "steamids": ",".join(steam_ids)}
        )

        if response.status_code == 429:
            if retry_count < 5:
                wait_time = (2 ** retry_count) * 60
                logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                return get_player_summaries_with_backoff(steam_ids, retry_count + 1)
            else:
                logger.error("Max retries reached for rate limit")
                return {}

        response.raise_for_status()
        data = response.json()
        players = data.get("response", {}).get("players", [])

        return {player["steamid"]: player for player in players}
    except Exception as e:
        logger.error(f"Error fetching player summaries: {e}")
        return {}

def get_playing_profiles(profiles_to_watch) -> dict:
    steam_ids = []
    profile_map = {}

    for profile in profiles_to_watch:
        steam_id = get_steam_id(profile)
        if steam_id:
            steam_ids.append(steam_id)
            profile_map[steam_id] = profile

    if not steam_ids:
        logger.error("No valid Steam profiles to watch")
        time.sleep(offline_check_interval)
        return playing_profiles

    player_data = get_player_summaries_with_backoff(steam_ids)

    if not player_data:
        time.sleep(offline_check_interval)
        return playing_profiles

    someone_playing = False

    for steam_id, data in player_data.items():
        profile = profile_map[steam_id]
        game = None
        status = SteamKind.NOT_PLAYING

        if "gameextrainfo" in data:
            status = SteamKind.PLAYING
            game = data["gameextrainfo"]
            someone_playing = True

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

    check_interval = active_check_interval if someone_playing else offline_check_interval
    time.sleep(check_interval)

    return playing_profiles

def main():
    if not steam_api_key:
        logger.error("STEAM_API_KEY environment variable is required")
        return

    logger.info(f"Starting Steam monitor for {len(profiles_to_watch)} profiles")
    logger.info(f"Active check interval: {active_check_interval}s")
    logger.info(f"Offline check interval: {offline_check_interval}s")

    while True:
        profiles = get_playing_profiles(profiles_to_watch)

if __name__ == "__main__":
    main()
