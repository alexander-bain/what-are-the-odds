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

# Global cache
cached_games = {}

def fetch_all_games_by_group():
    """Fetches all games grouped by sport."""
    global cached_games
    pacific_tz = timezone("US/Pacific")
    now = datetime.now(pacific_tz)
    games_by_group = {}

    for sport_key, group_name in INCLUDED_SPORTS.items():
        fetch_games_and_scores(sport_key, group_name, games_by_group, pacific_tz, now)

    cached_games = games_by_group
    return games_by_group


def fetch_games_and_scores(sport_key, group_name, games_by_group, pacific_tz, now):
    """Fetches games and their live scores for a specific sport."""
    odds_url = f"{BASE_URL}/{sport_key}/odds/?apiKey={API_KEY}&regions=us&markets=h2h"
    scores_url = f"{BASE_URL}/{sport_key}/scores/?apiKey={API_KEY}"
    
    try:
        # Fetch odds
        odds_response = requests.get(odds_url)
        odds_response.raise_for_status()
        odds_data = odds_response.json()

        # Fetch scores
        scores_response = requests.get(scores_url)
        scores_response.raise_for_status()
        scores_data = scores_response.json()

        # Create a scores lookup dictionary
        scores_lookup = {}
        scores_lookup = {}
        for score_entry in scores_data:
            game_id = score_entry.get('id')
            scores = score_entry.get('scores', [])
            
            home_score = "N/A"
            away_score = "N/A"
            for score in scores or []:
                if score.get('name') == score_entry.get('home_team'):
                    home_score = score.get('score', "N/A")
                elif score.get('name') == score_entry.get('away_team'):
                    away_score = score.get('score', "N/A")
            
            scores_lookup[game_id] = {
                'home_score': home_score,
                'away_score': away_score
            }

        games = []
        for game in odds_data:
            try:
                game_id = game.get("id")  # Get the API's game ID
                home_team = game.get("home_team", "N/A")
                away_team = game.get("away_team", "N/A")
                commence_time = game.get("commence_time", "N/A")

                # Convert times to Pacific
                commence_time_utc = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                commence_time_pacific = commence_time_utc.astimezone(pacific_tz).strftime("%Y-%m-%d %I:%M %p")

                # Look up scores
                game_key = f"{home_team} vs {away_team}"
                home_score = scores_lookup.get(game_id, {}).get('home_score', "N/A")
                away_score = scores_lookup.get(game_id, {}).get('away_score', "N/A")

                # Compute win probabilities
                bookmakers = game.get("bookmakers", [])
                home_probs, away_probs = [], []

                for bookmaker in bookmakers:
                    for market in bookmaker.get("markets", []):
                        if market["key"] == "h2h":
                            outcomes = market.get("outcomes", [])
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

                games.append({
                    "id": game_id,  # Store the API's game ID
                    "Sport": group_name,
                    "Game": f"{home_team} vs {away_team}",
                    "CommenceTime": commence_time_pacific,
                    "HomeWinProb": avg_home_prob,
                    "AwayWinProb": avg_away_prob,
                    "HomeScore": home_score,
                    "AwayScore": away_score,
                })
            except Exception as e:
                print(f"DEBUG: Error processing game: {e}")

        if games:
            if group_name not in games_by_group:
                games_by_group[group_name] = {"today": [], "upcoming": []}
            for game in games:
                commence_time = datetime.strptime(game["CommenceTime"], "%Y-%m-%d %I:%M %p").replace(tzinfo=pacific_tz)
                if commence_time.date() == now.date():
                    games_by_group[group_name]["today"].append(game)
                else:
                    games_by_group[group_name]["upcoming"].append(game)

    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Error fetching odds and scores for {sport_key}: {e}")

def get_game_by_id(game_id):
    """Finds a specific game in the cached games using the API's game ID."""
    global cached_games
    
    # Refresh cache if empty
    if not cached_games:
        fetch_all_games_by_group()
    
    # Look through cached games
    for group, games in cached_games.items():
        for section in ['today', 'upcoming']:
            for game in games[section]:
                if game['id'] == game_id:
                    return game
    
    return None

# Test the debug print
if __name__ == "__main__":
    fetch_all_games_by_group()