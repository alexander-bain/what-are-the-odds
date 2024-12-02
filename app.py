from flask import Flask, jsonify, render_template, request
from fetch_odds import fetch_all_games_by_group, cached_games  # Add cached_games to import

app = Flask(__name__)

@app.route('/')
def index():
    """Renders the main page with game data."""
    try:
        games = fetch_all_games_by_group()
        return render_template('index.html', sorted_games=games)
    except Exception as e:
        return f"An error occurred: {e}", 500

@app.route('/watching')
def watching():
    """Renders the watching page for a specific game."""
    try:
        game_id = request.args.get('id')
        
        games = fetch_all_games_by_group()
        
        # Find the specific game
        for group, group_games in games.items():
            for section in ['today', 'upcoming']:
                for game in group_games[section]:
                    if game['id'] == game_id:
                        return render_template('watching.html', game=game)
        
        return "Game not found", 404
    except Exception as e:
        return f"An error occurred: {e}", 500

@app.route('/api/get_probability')
def get_probability():
    """API endpoint to fetch updated probability for a specific game."""
    try:
        game_id = request.args.get('id')

        # Refresh cached data
        games = fetch_all_games_by_group()
        
        # Find the specific game
        for group, group_games in games.items():
            for section in ['today', 'upcoming']:
                for game in group_games[section]:
                    if game['id'] == game_id:
                        return jsonify({
                            'home_prob': game['HomeWinProb'],
                            'away_prob': game['AwayWinProb'],
                            'sportsbooks': game['SportsbookProbs']
                        })
        
        return jsonify({"error": "Game not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_scores')
def get_scores():
    """API endpoint to fetch scores for all games."""
    try:
        games = fetch_all_games_by_group()
        scores = []
        
        for group, group_games in games.items():
            for section in ['today', 'upcoming']:
                for game in group_games[section]:
                    scores.append({
                        'game': game['Game'],
                        'home_team': game['Game'].split(' vs ')[0],
                        'away_team': game['Game'].split(' vs ')[1],
                        'home_score': game['HomeScore'],
                        'away_score': game['AwayScore']
                    })
        
        return jsonify(scores)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)