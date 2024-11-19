from flask import Flask, render_template, request
import requests
from datetime import datetime

app = Flask(__name__)

API_KEY = '7d876eee43b66d431401bf58f1b3a8b0'
BASE_URL = 'https://api.the-odds-api.com/v4/sports'

def fetch_odds_for_team(team_name, bookmaker_filter):
    """Fetch odds for games involving the specified team with bookmaker filter."""
    sport = 'basketball_nba'
    region = 'us'
    url = f"{BASE_URL}/{sport}/odds/?apiKey={API_KEY}&regions={region}"

    response = requests.get(url)
    response.raise_for_status()
    odds_data = response.json()

    results = []
    for game in odds_data:
        home_team = game['home_team']
        away_team = game['away_team']

        if team_name.lower() in home_team.lower() or team_name.lower() in away_team.lower():
            commence_time = format_datetime(game['commence_time'])
            for bookmaker in game['bookmakers']:
                if bookmaker_filter and bookmaker['title'] != bookmaker_filter:
                    continue  # Skip bookmakers that don't match the filter
                
                for market in bookmaker['markets']:
                    if market['key'] == 'h2h':  # Head-to-head market
                        for outcome in market['outcomes']:
                            results.append({
                                'Game': f"{home_team} vs {away_team}",
                                'CommenceTime': commence_time,
                                'Bookmaker': bookmaker['title'],
                                'Outcome': outcome['name'],
                                'WinProbability': calculate_win_probability(outcome['price'])
                            })
    return results


def calculate_win_probability(odds):
    """Convert decimal odds to implied win probability."""
    return round(1 / odds * 100, 2)

def format_datetime(iso_string):
    """Convert ISO 8601 datetime string to human-readable format."""
    dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    return dt.strftime("%Y-%m-%d %I:%M %p")

@app.route('/', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def index():
    odds = []
    team_name = ""
    bookmaker_filter = ""

    if request.method == 'POST':
        team_name = request.form.get('team_name', '').strip()
        bookmaker_filter = request.form.get('bookmaker', '').strip()

        if team_name:
            try:
                odds = fetch_odds_for_team(team_name, bookmaker_filter)
            except Exception as e:
                print(f"Error fetching odds: {e}")

    return render_template('index.html', odds=odds, team_name=team_name)

if __name__ == '__main__':
    app.run(debug=True)