from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scores.db'
db = SQLAlchemy(app)

LIMIT_DATE = datetime(2025, 11, 5, 23, 59, 59)  # Fecha límite evento

# --- Modelo de puntuación ---
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(50))
    score = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# --- Función para inicializar la base de datos ---
def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Base de datos creada correctamente")

# --- Endpoints ---
@app.route('/score', methods=['POST'])
def add_score():
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

# --- Main ---
if __name__ == '__main__':
    init_db()       # Inicializa la base de datos dentro del contexto
    app.run(host='0.0.0.0', port=5000)