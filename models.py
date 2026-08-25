from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50))
    age = db.Column(db.Integer)
    batting_style = db.Column(db.String(50))
    bowling_style = db.Column(db.String(50))
    nationality = db.Column(db.String(50))
    image_path = db.Column(db.String(200))
    sold = db.Column(db.Boolean, default=False)
    sold_price = db.Column(db.Float, default=0.0)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    team = db.relationship('Team', backref='players', foreign_keys=[team_id])

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    owner = db.Column(db.String(100))
    logo_path = db.Column(db.String(200))
    remaining_funds = db.Column(db.Float, default=0.0)

class AuctionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    sold_price = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    player = db.relationship('Player', backref='auction_logs')
    team = db.relationship('Team', backref='auction_logs')