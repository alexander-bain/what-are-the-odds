import requests
import csv
from datetime import datetime

API_KEY = '7d876eee43b66d431401bf58f1b3a8b0'
BASE_URL = 'https://api.the-odds-api.com/v4/sports'

def fetch_and_filter_odds():
    # Prompt user for a team name
    while True:
        team_name = input("Enter a team name to filter by: ").strip()
        if not team_name:
            print("Error: Team name cannot be empty. Please try again.")
        elif not team_name.isalpha():
            print("Error: Team name should only contain letters. Please try again.")
        else:
            break

    team_name = team_name.lower()  # Convert to lowercase for comparison

    sport = 'basketball_nba'  # Replace with your chosen sport
    region = 'us'  # Adjust region if needed
    url = f"{BASE_URL}/{sport}/odds/?apiKey={API_KEY}&regions={region}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP status codes 4xx/5xx

        odds_data = response.json()
        print(f"\nFiltering games for team: {team_name.capitalize()}\n")

        found_games = False
        results = []
        for game in odds_data:
            home_team = game['home_team']
            away_team = game['away_team']

            # Check if the team is in this game
            if team_name in home_team.lower() or team_name in away_team.lower():
                found_games = True
                commence_time = format_datetime(game['commence_time'])
                print(f"\nGame: {home_team} vs {away_team}")
                print(f"Commence Time: {commence_time}")

                for bookmaker in game['bookmakers']:
                    print(f"  Bookmaker: {bookmaker['title']}")
                    for market in bookmaker['markets']:
                        if market['key'] == 'h2h':  # Head-to-head market
                            for outcome in market['outcomes']:
                                print(f"    {outcome['name']}: {outcome['price']}")

                                # Save result to the list
                                results.append({
                                    'Game': f"{home_team} vs {away_team}",
                                    'Commence Time': commence_time,
                                    'Bookmaker': bookmaker['title'],
                                    'Outcome': outcome['name'],
                                    'Odds': outcome['price']
                                })

        if not found_games:
            print(f"No games found for team: {team_name.capitalize()}")
        else:
            # Save results to a CSV file
            save_to_csv(team_name, results)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
    except KeyError as e:
        print(f"Error parsing response: Missing key {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def format_datetime(iso_string):
    """Convert ISO 8601 datetime string to human-readable format."""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))  # Handle timezone-aware ISO strings
        return dt.strftime("%Y-%m-%d %I:%M %p")  # Format: YYYY-MM-DD HH:MM AM/PM
    except Exception as e:
        print(f"Error formatting datetime: {e}")
        return iso_string  # Return original if formatting fails


def save_to_csv(team_name, results):
    # Generate a timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{team_name}_odds_{timestamp}.csv"

    # Define CSV column headers
    fieldnames = ['Game', 'Commence Time', 'Bookmaker', 'Outcome', 'Odds']

    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"\nData successfully saved to {filename}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")


if __name__ == "__main__":
    fetch_and_filter_odds()