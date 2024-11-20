from flask import Flask, render_template, request, jsonify
from fetch_odds import fetch_all_games_by_group

app = Flask(__name__)

@app.route('/')
def index():
    # Fetch sorted games from fetch_odds
    sorted_games = fetch_all_games_by_group()

    # Temporarily print sorted games for debugging
    print(f"DEBUG: Sorted Games: {sorted_games}")

    # Render the template with sorted games
    return render_template('index.html', sorted_games=sorted_games)

@app.route('/watching')
def watching():
    sport = request.args.get("sport")
    home_team = request.args.get("home")
    away_team = request.args.get("away")

    # Fetch the latest probabilities for this game
    games_by_group = fetch_all_games_by_group()
    game_data = None
    for group, games in games_by_group.items():
        for game in games["upcoming"] + games["today"]:
            if game["Game"] == f"{home_team} vs {away_team}":
                game_data = game
                break
        if game_data:
            break

    if not game_data:
        return render_template("error.html", message="Game not found"), 404

    return render_template("watching.html", game=game_data)

@app.route('/api/get_probability')
def get_probability():
    sport = request.args.get("sport")
    home_team = request.args.get("home")
    away_team = request.args.get("away")

    games_by_group = fetch_all_games_by_group()
    game_data = None
    for group, games in games_by_group.items():
        for game in games["upcoming"] + games["today"]:
            if game["Game"] == f"{home_team} vs {away_team}":
                game_data = game
                break
        if game_data:
            break

    if game_data:
        return jsonify({
            "home_prob": game_data["HomeWinProb"],
            "away_prob": game_data["AwayWinProb"]
        })
    else:
        return jsonify({"error": "Game not found"}), 404

if __name__ == '__main__':
    app.run(debug=False)  # Turn off debugging for production