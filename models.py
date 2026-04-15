from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from datetime import datetime

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, connection_record):
    """SQLite için FOREIGN KEY kısıtlamalarını aktif et."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    logo_url = db.Column(db.String(200), default='')

    def __repr__(self):
        return f'<Team {self.name}>'


class Match(db.Model):
    """İki takım + iki skor. Ev/deplasman yok."""
    id = db.Column(db.Integer, primary_key=True)
    team1_id = db.Column(
        db.Integer,
        db.ForeignKey('team.id', ondelete='CASCADE'),
        nullable=False
    )
    team2_id = db.Column(
        db.Integer,
        db.ForeignKey('team.id', ondelete='CASCADE'),
        nullable=False
    )
    team1_score = db.Column(db.Integer, nullable=False, default=0)
    team2_score = db.Column(db.Integer, nullable=False, default=0)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, default='')

    team1 = db.relationship('Team', foreign_keys=[team1_id])
    team2 = db.relationship('Team', foreign_keys=[team2_id])
    photos = db.relationship(
        'MatchPhoto',
        backref='match',
        cascade='all, delete-orphan',
        order_by='MatchPhoto.uploaded_at.desc()'
    )

    def __repr__(self):
        return f'<Match {self.team1.name} vs {self.team2.name}>'


class Scorer(db.Model):
    """Gol krallığı — turnuva geneli. Admin manuel gol sayısını günceller."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    goals = db.Column(db.Integer, default=0, nullable=False)
    team_id = db.Column(
        db.Integer,
        db.ForeignKey('team.id', ondelete='SET NULL'),
        nullable=True
    )
    team = db.relationship('Team')

    def __repr__(self):
        return f'<Scorer {self.name} ({self.goals})>'


class MatchPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(
        db.Integer,
        db.ForeignKey('match.id', ondelete='CASCADE'),
        nullable=False
    )
    filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255), default='')
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MatchPhoto {self.filename}>'


def _base_stats(team_id, matches):
    played = wins = draws = losses = gf = ga = 0
    for m in matches:
        if m.team1_id == team_id:
            own, opp = m.team1_score, m.team2_score
        else:
            own, opp = m.team2_score, m.team1_score
        played += 1
        gf += own
        ga += opp
        if own > opp:
            wins += 1
        elif own == opp:
            draws += 1
        else:
            losses += 1
    points = wins * 3 + draws
    return {
        'played': played, 'wins': wins, 'draws': draws, 'losses': losses,
        'gf': gf, 'ga': ga, 'goal_diff': gf - ga, 'points': points
    }


def _head_to_head_stats(team_ids, all_matches):
    id_set = set(team_ids)
    mini = [m for m in all_matches
            if m.team1_id in id_set and m.team2_id in id_set]
    result = {}
    for tid in team_ids:
        team_mini = [m for m in mini
                     if m.team1_id == tid or m.team2_id == tid]
        result[tid] = _base_stats(tid, team_mini)
    return result


def calculate_standings():
    """
    TFF kuralları: puan > ikili averaj puanı > ikili averaj > ikili gol > genel averaj > genel gol
    """
    teams = Team.query.all()
    all_matches = Match.query.all()

    rows = []
    for t in teams:
        team_matches = [m for m in all_matches
                        if m.team1_id == t.id or m.team2_id == t.id]
        s = _base_stats(t.id, team_matches)
        s['team'] = t
        s['team_id'] = t.id
        rows.append(s)

    rows.sort(key=lambda r: (-r['points'], -r['goal_diff'], -r['gf']))

    final = []
    i = 0
    while i < len(rows):
        j = i
        while j + 1 < len(rows) and rows[j + 1]['points'] == rows[i]['points']:
            j += 1

        group = rows[i:j + 1]
        if len(group) == 1:
            final.extend(group)
        else:
            ids = [r['team_id'] for r in group]
            h2h = _head_to_head_stats(ids, all_matches)
            group.sort(key=lambda r: (
                -h2h[r['team_id']]['points'],
                -h2h[r['team_id']]['goal_diff'],
                -h2h[r['team_id']]['gf'],
                -r['goal_diff'],
                -r['gf'],
            ))
            final.extend(group)
        i = j + 1

    return final
