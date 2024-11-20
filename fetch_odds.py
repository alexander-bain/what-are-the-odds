import requests
from datetime import datetime
from pytz import timezone

API_KEY = "396119decf15c527df766e99d5b8dce4"
BASE_URL = "https://api.the-odds-api.com/v4/sports"
EXCLUDED_GROUPS = ["Soccer", "Rugby League", "Rugby Union", "Cricket", "Boxing", "Aussie Rules", "Ice Hockey"]
INCLUDED_SPORTS = {
    "americanfootball_nfl": "NFL",
    "americanfootball_ncaaf": "NCAAF",
    "basketball_nba": "NBA",
    "basketball_ncaab": "NCAAB",
}

def fetch_all_games_by_group():
    pacific_tz = timezone("US/Pacific")
    now = datetime.now(pacific_tz)

    games_by_group = {}

    # Explicitly fetch key sports
    for sport_key, group_name in INCLUDED_SPORTS.items():
        fetch_games_for_sport(sport_key, group_name, games_by_group, pacific_tz, now)

    # Dynamically fetch remaining sports
    try:
        url = f"{BASE_URL}/?apiKey={API_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        sports_data = response.json()

        for sport in sports_data:
            sport_key = sport["key"]
            group = sport.get("group", "Other")

            # Skip excluded groups or included sports
            if group in EXCLUDED_GROUPS or sport_key in INCLUDED_SPORTS:
                continue

            fetch_games_for_sport(sport_key, group, games_by_group, pacific_tz, now)

    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Error fetching sports data: {e}")

    if not games_by_group:
        print("DEBUG: No games found in any category.")

    return games_by_group


def fetch_games_for_sport(sport_key, group_name, games_by_group, pacific_tz, now):
    url = f"{BASE_URL}/{sport_key}/odds/?apiKey={API_KEY}&regions=us&markets=h2h"
    try:
        response = requests.get(url)
        response.raise_for_status()
        odds_data = response.json()

        if not odds_data:
            return

        games = []
        for game in odds_data:
            try:
                home_team = game["home_team"]
                away_team = game["away_team"]
                commence_time = game["commence_time"]
                bookmakers = game.get("bookmakers", [])
            except KeyError as e:
                print(f"DEBUG: Missing key in game data: {e}")
                continue

            home_probs, away_probs = [], []
            for bookmaker in bookmakers:
                for market in bookmaker.get("markets", []):
                    if market["key"] == "h2h":
                        outcomes = market["outcomes"]
                        home_odds = next((o["price"] for o in outcomes if o["name"] == home_team), None)
                        away_odds = next((o["price"] for o in outcomes if o["name"] == away_team), None)

                        if home_odds and away_odds:
                            home_prob = 1 / home_odds
                            away_prob = 1 / away_odds
                            total_prob = home_prob + away_prob
                            home_probs.append((home_prob / total_prob) * 100)
                            away_probs.append((away_prob / total_prob) * 100)

            avg_home_prob = round(sum(home_probs) / len(home_probs)) if home_probs else "N/A"
            avg_away_prob = round(sum(away_probs) / len(away_probs)) if away_probs else "N/A"

            commence_time_utc = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            commence_time_pacific = commence_time_utc.astimezone(pacific_tz).strftime("%Y-%m-%d %I:%M %p")

            games.append({
                "Sport": group_name,
                "Game": f"{home_team} vs {away_team}",
                "CommenceTime": commence_time_pacific,
                "HomeWinProb": avg_home_prob,
                "AwayWinProb": avg_away_prob,
            })

        if games:
            if group_name not in games_by_group:
                games_by_group[group_name] = {"today": [], "upcoming": []}
            for game in games:
                commence_time = datetime.strptime(game["CommenceTime"], "%Y-%m-%d %I:%M %p").replace(tzinfo=pacific_tz)
                if commence_time.date() == now.date():
                    games_by_group[group_name]["today"].append(game)
                elif commence_time > now:
                    games_by_group[group_name]["upcoming"].append(game)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            print(f"DEBUG: Unsupported market for sport: {sport_key}")
        else:
            print(f"DEBUG: HTTP error fetching odds for {sport_key}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Error fetching odds for {sport_key}: {e}")