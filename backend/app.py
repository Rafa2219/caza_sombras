from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scores.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(50))
    score = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy', 
        'message': 'Servidor funcionando',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/score', methods=['POST'])
def add_score():
    try:
        data = request.get_json()
        discord_id = data.get('discord_id')
        score = data.get('score')
        
        new_score = Score(discord_id=discord_id, score=score)
        db.session.add(new_score)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Puntuación guardada'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/scores', methods=['GET'])
def get_scores():
    try:
        scores = Score.query.order_by(Score.score.asc()).limit(10).all()
        return jsonify([
            {
                'discord_id': s.discord_id,
                'score': s.score,
                'date': s.date.isoformat() if s.date else None
            }
            for s in scores
        ])
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Base de datos inicializada")

if __name__ == '__main__':
    init_db()
    print("🚀 Servidor en http://0.0.0.0:5000")
    print("📊 Endpoints: /health, /score, /scores")
    app.run(host='0.0.0.0', port=5000, debug=True)