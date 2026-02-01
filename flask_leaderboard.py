from flask import Flask, jsonify, request, render_template_string
from datetime import datetime
import json
import os

app = Flask(__name__)

# Store leaderboard data in memory and persist to JSON
LEADERBOARD_FILE = "leaderboard.json"

def load_leaderboard():
    """Load leaderboard from JSON file"""
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, 'r') as f:
            return json.load(f)
    return []

def save_leaderboard(data):
    """Save leaderboard to JSON file"""
    with open(LEADERBOARD_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/api/submit_run', methods=['POST'])
def submit_run():
    """API endpoint to submit a new run to the leaderboard"""
    try:
        data = request.json
        
        # Validate required fields
        if not all(k in data for k in ['score', 'duration', 'signature']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        run_entry = {
            'timestamp': datetime.now().isoformat(),
            'score': int(data['score']),
            'duration_ms': int(data['duration']),
            'signature': data['signature'],
            'robot_id': data.get('robot_id', 'UNKNOWN')
        }
        
        # Load, add, and save
        leaderboard = load_leaderboard()
        leaderboard.append(run_entry)
        save_leaderboard(leaderboard)
        
        return jsonify({'status': 'success', 'entry': run_entry}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard sorted by score (descending) then time (ascending)"""
    leaderboard = load_leaderboard()
    
    # Sort by score (descending), then by time (ascending)
    sorted_board = sorted(leaderboard, key=lambda x: (-x['score'], x['duration_ms']))
    
    return jsonify(sorted_board)

@app.route('/')
def leaderboard_page():
    """Display the leaderboard as an HTML page"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>UTRA Hacks 2026 - Leaderboard</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1000px;
                margin: 0 auto;
            }
            
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 10px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            
            .subtitle {
                color: rgba(255,255,255,0.9);
                text-align: center;
                margin-bottom: 30px;
                font-size: 1.1em;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }
            
            thead {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            th {
                padding: 15px;
                text-align: left;
                font-weight: 600;
            }
            
            td {
                padding: 12px 15px;
                border-bottom: 1px solid #eee;
            }
            
            tbody tr {
                transition: background 0.3s ease;
            }
            
            tbody tr:hover {
                background: #f5f5f5;
            }
            
            tbody tr:nth-child(1) {
                background: #fffacd;
                font-weight: bold;
            }
            
            tbody tr:nth-child(2) {
                background: #f0f0f0;
            }
            
            tbody tr:nth-child(3) {
                background: #ffe4b5;
            }
            
            .rank {
                font-weight: bold;
                font-size: 1.2em;
                width: 50px;
            }
            
            .rank-1::before {
                content: "🥇 ";
            }
            
            .rank-2::before {
                content: "🥈 ";
            }
            
            .rank-3::before {
                content: "🥉 ";
            }
            
            .tx-link {
                color: #667eea;
                text-decoration: none;
                word-break: break-all;
                font-size: 0.85em;
            }
            
            .tx-link:hover {
                text-decoration: underline;
            }
            
            .loading {
                text-align: center;
                color: white;
                font-size: 1.2em;
                padding: 40px;
            }
            
            .refresh-info {
                text-align: center;
                color: rgba(255,255,255,0.8);
                margin-top: 20px;
                font-size: 0.9em;
            }
            
            .empty-state {
                text-align: center;
                padding: 40px;
                color: #999;
                font-size: 1.1em;
            }
        </style>
        <meta http-equiv="refresh" content="5">
    </head>
    <body>
        <div class="container">
            <h1>🚀 UTRA HACKS 2026</h1>
            <p class="subtitle">Biathlon Leaderboard</p>
            
            <div id="leaderboard-container">
                <div class="loading">Loading leaderboard...</div>
            </div>
            
            <div class="refresh-info">⟲ Auto-refreshing every 5 seconds</div>
        </div>
        
        <script>
            async function loadLeaderboard() {
                try {
                    const response = await fetch('/api/leaderboard');
                    const data = await response.json();
                    
                    if (data.length === 0) {
                        document.getElementById('leaderboard-container').innerHTML = 
                            '<div class="empty-state">No runs yet. Waiting for competitors...</div>';
                        return;
                    }
                    
                    let html = `
                        <table>
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Robot ID</th>
                                    <th>Score</th>
                                    <th>Time (ms)</th>
                                    <th>Timestamp</th>
                                    <th>Transaction</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;
                    
                    data.forEach((entry, index) => {
                        const rank = index + 1;
                        const rankClass = rank <= 3 ? `rank-${rank}` : '';
                        const shortSig = entry.signature.substring(0, 16) + '...';
                        const explorerUrl = `https://explorer.solana.com/tx/${entry.signature}?cluster=devnet`;
                        const timestamp = new Date(entry.timestamp).toLocaleString();
                        
                        html += `
                            <tr>
                                <td class="rank ${rankClass}">${rank}</td>
                                <td>${entry.robot_id}</td>
                                <td><strong>${entry.score}</strong></td>
                                <td>${entry.duration_ms}</td>
                                <td>${timestamp}</td>
                                <td><a href="${explorerUrl}" target="_blank" class="tx-link">${shortSig}</a></td>
                            </tr>
                        `;
                    });
                    
                    html += '</tbody></table>';
                    document.getElementById('leaderboard-container').innerHTML = html;
                    
                } catch (error) {
                    document.getElementById('leaderboard-container').innerHTML = 
                        '<div class="empty-state">Error loading leaderboard</div>';
                    console.error('Error:', error);
                }
            }
            
            // Load immediately and then refresh periodically
            loadLeaderboard();
            setInterval(loadLeaderboard, 5000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
