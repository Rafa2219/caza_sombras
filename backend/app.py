from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scores.db'
db = SQLAlchemy(app)

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(50))
    score = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# --- Crear las tablas dentro del contexto de la app ---
with app.app_context():
    db.create_all()

# --- Resto del código ---
LIMIT_DATE = datetime(2025, 11, 5, 23, 59, 59)

@app.route('/score', methods=['POST'])
def add_score():
    from flask import request, jsonify
    now = datetime.utcnow()
    if now > LIMIT_DATE:
        return jsonify({'status':'error','message':'El evento ha terminado'}), 403

    data = request.get_json()
    discord_id = data.get('discord_id')
    score = data.get('score')
    if not discord_id or score is None:
        return jsonify({'status':'error','message':'Datos incompletos'}), 400

    new_score = Score(discord_id=discord_id, score=score)
    db.session.add(new_score)
    db.session.commit()
    return jsonify({'status':'success','message':'Puntaje guardado correctamente'})

@app.route('/scores', methods=['GET'])
def get_scores():
    top_scores = Score.query.filter(Score.date <= LIMIT_DATE).order_by(Score.score.desc()).limit(10).all()
    return jsonify([
        {'discord_id': s.discord_id, 'score': s.score, 'date': s.date.isoformat()}
        for s in top_scores
    ])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)