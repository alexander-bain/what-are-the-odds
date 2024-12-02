import requests
from datetime import datetime
from pytz import timezone

API_KEY = "396119decf15c527df766e99d5b8dce4"
BASE_URL = "https://api.the-odds-api.com/v4/sports"
INCLUDED_SPORTS = {
    "americanfootball_nfl": "NFL",
    "americanfootball_ncaaf": "NCAAF",
    "basketball_nba": "NBA",
    "basketball_ncaab": "NCAAB",
}
cached_games = {}  # Global cache to store fetched games


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
    """Fetches games and live scores for a specific sport."""
    odds_url = f"{BASE_URL}/{sport_key}/odds/?apiKey={API_KEY}&regions=us&markets=h2h,spreads,totals"
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

        # Create a lookup dictionary for scores
        scores_lookup = create_scores_lookup(scores_data)

        games = []
        for game in odds_data:
            try:
                # Process game data
                game_data = process_game_data(game, scores_lookup, group_name, pacific_tz)
                if game_data:  # Only append if we got valid game data
                    games.append(game_data)
            except Exception as e:
                print(f"DEBUG: Error processing game: {e}")

        # Organize games into "today" and "upcoming"
        organize_games_by_date(games, games_by_group, group_name, now, pacific_tz)

    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Error fetching odds and scores for {sport_key}: {e}")

def calculate_implied_scores(total, spread):
    """Calculate implied scores based on the total and spread."""
    if total is None or spread is None:
        return None, None
    
    favored_team_score = (total + abs(spread)) / 2
    underdog_team_score = (total - abs(spread)) / 2
    return round(favored_team_score, 1), round(underdog_team_score, 1)

def create_scores_lookup(scores_data):
    """Creates a lookup dictionary for game scores."""
    scores_lookup = {}
    for score_entry in scores_data:
        game_id = score_entry.get('id')
        scores = score_entry.get('scores', [])
        completed = score_entry.get('completed', False)  # Get completed status from API

        home_score = "N/A"
        away_score = "N/A"
        for score in scores or []:
            if score.get('name') == score_entry.get('home_team'):
                home_score = score.get('score', "N/A")
            elif score.get('name') == score_entry.get('away_team'):
                away_score = score.get('score', "N/A")

        scores_lookup[game_id] = {
            'home_score': home_score,
            'away_score': away_score,
            'completed': completed  # Store completed status
        }
    return scores_lookup


def process_game_data(game, scores_lookup, group_name, pacific_tz):
    """Processes a single game and extracts relevant data."""
    game_id = game.get("id")
    home_team = game.get("home_team", "N/A")
    away_team = game.get("away_team", "N/A")
    commence_time = game.get("commence_time", "N/A")

    # Convert commence time to Pacific Time
    commence_time_utc = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
    commence_time_pacific = commence_time_utc.astimezone(pacific_tz).strftime("%Y-%m-%d %I:%M %p")

    # Lookup scores and status
    game_scores = scores_lookup.get(game_id, {})
    home_score = game_scores.get('home_score', "N/A")
    away_score = game_scores.get('away_score', "N/A")
    completed = game_scores.get('completed', False)

    # Get market data
    sportsbook_probs, avg_home_prob, avg_away_prob = compute_probabilities(game, home_team, away_team)
    total, spread, sportsbook_implied_scores = get_total_and_spread(game, home_team)

    # Calculate implied scores
    implied_home_score, implied_away_score = calculate_implied_scores(total, spread)
    is_home_favored = spread is not None and spread < 0

    return {
        "id": game_id,
        "Sport": group_name,
        "Game": f"{home_team} vs {away_team}",
        "CommenceTime": commence_time_pacific,
        "HomeWinProb": avg_home_prob,
        "AwayWinProb": avg_away_prob,
        "HomeScore": home_score,
        "AwayScore": away_score,
        "completed": completed,
        "SportsbookProbs": sportsbook_probs,
        "Total": total,
        "Spread": spread,
        "ImpliedHomeScore": implied_home_score,
        "ImpliedAwayScore": implied_away_score,
        "IsHomeFavored": is_home_favored,
        "SportsbookImpliedScores": sportsbook_implied_scores
    }

def get_total_and_spread(game, home_team):
    """Extract and aggregate totals and spreads from all bookmakers."""
    bookmakers = game.get("bookmakers", [])
    if not bookmakers:
        return None, None, {}

    totals = []
    spreads = []
    sportsbook_implied_scores = {}

    for bookmaker in bookmakers:
        book_name = bookmaker.get("title", "Unknown")
        book_total = None
        book_spread = None

        for market in bookmaker.get("markets", []):
            if market["key"] == "totals":
                for outcome in market.get("outcomes", []):
                    if outcome["name"] == "Over":
                        book_total = float(outcome["point"])
                        break
            
            elif market["key"] == "spreads":
                for outcome in market.get("outcomes", []):
                    if outcome["name"] == home_team:
                        book_spread = float(outcome["point"])
                        break

        if book_total is not None and book_spread is not None:
            totals.append(book_total)
            spreads.append(book_spread)
            home_score, away_score = calculate_implied_scores(book_total, book_spread)
            if home_score is not None and away_score is not None:
                sportsbook_implied_scores[book_name] = {
                    "HomeScore": home_score,
                    "AwayScore": away_score,
                    "Total": book_total,
                    "Spread": book_spread
                }

    if not totals or not spreads:
        return None, None, {}

    avg_total = sum(totals) / len(totals)
    avg_spread = sum(spreads) / len(spreads)
    
    return round(avg_total, 1), round(avg_spread, 1), sportsbook_implied_scores

def compute_probabilities(game, home_team, away_team):
    """Computes win probabilities from sportsbook data."""
    bookmakers = game.get("bookmakers", [])
    sportsbook_probs = {}
    home_probs, away_probs = [], []

    for bookmaker in bookmakers:
        book_name = bookmaker.get("title", "Unknown")
        home_odds = away_odds = None

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

                    sportsbook_probs[book_name] = {
                        "HomeWinProb": round((home_prob / total_prob) * 100, 2),
                        "AwayWinProb": round((away_prob / total_prob) * 100, 2)
                    }

    avg_home_prob = round(sum(home_probs) / len(home_probs)) if home_probs else "N/A"
    avg_away_prob = round(sum(away_probs) / len(away_probs)) if away_probs else "N/A"

    return sportsbook_probs, avg_home_prob, avg_away_prob


def organize_games_by_date(games, games_by_group, group_name, now, pacific_tz):
    """Organizes games into 'today' and 'upcoming' sections."""
    if games:  # Only process if we have games
        if group_name not in games_by_group:
            games_by_group[group_name] = {"today": [], "upcoming": []}

        for game in games:
            commence_time = datetime.strptime(game["CommenceTime"], "%Y-%m-%d %I:%M %p").replace(tzinfo=pacific_tz)
            if commence_time.date() == now.date():
                games_by_group[group_name]["today"].append(game)
            else:
                games_by_group[group_name]["upcoming"].append(game)


def get_game_by_id(game_id):
    """Finds a specific game in the cached games using the API's game ID."""
    global cached_games

    # Refresh cache if empty
    if not cached_games:
        fetch_all_games_by_group()

    # Search for the game
    for group, games in cached_games.items():
        for section in ['today', 'upcoming']:
            for game in games[section]:
                if game['id'] == game_id:
                    return game

    return None


# Test the debug print
if __name__ == "__main__":
    fetch_all_games_by_group()