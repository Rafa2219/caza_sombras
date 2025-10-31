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
    discord_id = db.Column(db.String(50), unique=True)  # Único para cada usuario
    score = db.Column(db.Float)  # Cambiado a Float para decimales
    date = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def home():
    # Obtener el ID de Discord desde la URL si existe
    discord_id = request.args.get('id', '')
    return render_template('index.html', default_discord_id=discord_id)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "message": "Servidor funcionando"})

@app.route('/scores', methods=['GET'])
def get_scores():
    # Obtener mejores puntuaciones (menor score = mejor)
    scores = Score.query.order_by(Score.score.asc()).limit(10).all()
    return jsonify([{
        "discord_id": s.discord_id, 
        "score": round(s.score, 2),  # Redondear a 2 decimales
        "date": s.date.isoformat() if s.date else None
    } for s in scores])

@app.route('/score', methods=['POST'])
def add_score():
    try:
        data = request.get_json()
        discord_id = data.get('discord_id')
        score_value = float(data.get('score'))  # Convertir a float para decimales
        
        # Buscar si ya existe un registro para este usuario
        existing_score = Score.query.filter_by(discord_id=discord_id).first()
        
        if existing_score:
            # Si el nuevo score es mejor (menor), actualizar
            if score_value < existing_score.score:
                existing_score.score = score_value
                existing_score.date = datetime.utcnow()
                db.session.commit()
                return jsonify({
                    "status": "success", 
                    "message": "Puntuación actualizada (mejor marca)",
                    "action": "updated"
                })
            else:
                return jsonify({
                    "status": "success",
                    "message": "Puntuación no superada (mantienes tu mejor marca)",
                    "action": "not_improved"
                })
        else:
            # Nuevo usuario, crear registro
            new_score = Score(discord_id=discord_id, score=score_value)
            db.session.add(new_score)
            db.session.commit()
            return jsonify({
                "status": "success", 
                "message": "Puntuación guardada",
                "action": "created"
            })
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500

# Ruta para obtener/actualizar score específico de usuario
@app.route('/score/<discord_id>', methods=['GET'])
def get_user_score(discord_id):
    score = Score.query.filter_by(discord_id=discord_id).first()
    if score:
        return jsonify({
            "discord_id": score.discord_id,
            "score": round(score.score, 2),
            "date": score.date.isoformat() if score.date else None
        })
    else:
        return jsonify({"error": "Usuario no encontrado"}), 404

# Inicializar base de datos
with app.app_context():
    db.create_all()
    print("✅ Base de datos inicializada")
    print(f"📊 Registros: {Score.query.count()}")

if __name__ == '__main__':
    print("🚀 Servidor Flask iniciado en http://0.0.0.0:5000")
    print("📋 Rutas disponibles:")
    print("   GET  /               → Página principal (acepta ?id=Usuario)")
    print("   GET  /health         → Estado del servidor")
    print("   GET  /scores         → Ranking top 10")
    print("   POST /score          → Guardar/actualizar puntuación")
    print("   GET  /score/<user>   → Obtener puntuación de usuario")
    app.run(host='0.0.0.0', port=5000, debug=True)