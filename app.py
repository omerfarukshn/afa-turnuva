import os
import uuid
from functools import wraps
from pathlib import Path
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, session, send_from_directory, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps

from models import db, Team, Match, MatchPhoto, calculate_standings

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('TFF_SECRET_KEY', 'afa-turnuva-dev-secret')

# DB URL önceliği: DATABASE_URL → DATABASE_PATH → instance SQLite
_db_url = os.environ.get('DATABASE_URL')
if not _db_url:
    _db_path = os.environ.get('DATABASE_PATH')
    _db_url = f'sqlite:///{_db_path}' if _db_path else 'sqlite:///database.db'
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

# Uploads dizini:
#   Fly.io prod: UPLOADS_DIR=/data/uploads
#   Lokal: instance/uploads
UPLOADS_DIR = Path(os.environ.get('UPLOADS_DIR', Path(app.instance_path) / 'uploads'))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {'jpg', 'jpeg', 'png', 'webp', 'heic'}
MAX_PHOTOS_PER_MATCH = 30
MAX_IMAGE_DIMENSION = 1600   # uzun kenar
THUMB_DIMENSION = 500

db.init_app(app)

ADMIN_USER = os.environ.get('TFF_ADMIN_USER', 'admin')
ADMIN_PASS_HASH = generate_password_hash(os.environ.get('TFF_ADMIN_PASS', 'admin123'))


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Admin paneli için giriş yapmalısınız!')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrap


def _allowed_file(name):
    return '.' in name and name.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def _save_photo(file_storage, match_id):
    """Yüklenen fotoğrafı küçült + thumb üret + kaydet. filename döndürür."""
    if not file_storage or not file_storage.filename:
        return None
    if not _allowed_file(file_storage.filename):
        return None

    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    if ext == 'jpeg':
        ext = 'jpg'
    if ext == 'heic':
        ext = 'jpg'  # HEIC'i JPG'ye çeviririz (mobile için yaygın)

    name = f"{uuid.uuid4().hex}.{ext}"
    match_dir = UPLOADS_DIR / 'matches' / str(match_id)
    match_dir.mkdir(parents=True, exist_ok=True)

    target_full = match_dir / name
    target_thumb = match_dir / f"thumb_{name}"

    try:
        img = Image.open(file_storage.stream)
        img = ImageOps.exif_transpose(img)  # EXIF rotation düzelt
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Full (max 1600px)
        full = img.copy()
        full.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.LANCZOS)
        full.save(target_full, quality=85, optimize=True)

        # Thumb (max 500px)
        thumb = img.copy()
        thumb.thumbnail((THUMB_DIMENSION, THUMB_DIMENSION), Image.LANCZOS)
        thumb.save(target_thumb, quality=80, optimize=True)
    except Exception as e:
        app.logger.error(f"Görsel işleme hatası: {e}")
        if target_full.exists():
            target_full.unlink(missing_ok=True)
        if target_thumb.exists():
            target_thumb.unlink(missing_ok=True)
        return None

    return name


def _delete_photo_files(match_id, filename):
    match_dir = UPLOADS_DIR / 'matches' / str(match_id)
    for f in (match_dir / filename, match_dir / f"thumb_{filename}"):
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass


# ---------- Public Routes ----------

@app.route('/')
def index():
    standings = calculate_standings()
    recent = Match.query.order_by(Match.date.desc()).limit(5).all()
    return render_template('index.html', standings=standings, recent=recent)


@app.route('/matches')
def matches_list():
    matches = Match.query.order_by(Match.date.desc()).all()
    return render_template('matches.html', matches=matches)


@app.route('/matches/<int:match_id>')
def match_detail(match_id):
    match = Match.query.get_or_404(match_id)
    return render_template('match_detail.html', match=match)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded images from persistent dir."""
    return send_from_directory(UPLOADS_DIR, filename)


# ---------- Admin Auth ----------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USER and check_password_hash(ADMIN_PASS_HASH, password):
            session['logged_in'] = True
            flash('Admin paneline hoşgeldiniz!')
            return redirect(url_for('admin'))
        flash('Geçersiz kullanıcı adı veya şifre!')
    return render_template('admin_login.html')


@app.route('/admin/logout', methods=['POST'])
@login_required
def admin_logout():
    session.pop('logged_in', None)
    flash('Çıkış yapıldı.')
    return redirect(url_for('index'))


# ---------- Admin: Teams ----------

@app.route('/admin', methods=['GET'])
@login_required
def admin():
    teams = Team.query.order_by(Team.name).all()
    matches = Match.query.order_by(Match.date.desc()).all()
    return render_template('admin.html', teams=teams, matches=matches)


@app.route('/admin/team_add', methods=['POST'])
@login_required
def team_add():
    name = request.form.get('team_name', '').strip()
    if name and not Team.query.filter_by(name=name).first():
        db.session.add(Team(name=name))
        db.session.commit()
        flash(f'Takım "{name}" eklendi.')
    else:
        flash('Takım adı geçersiz veya mevcut!')
    return redirect(url_for('admin'))


@app.route('/admin/team_delete/<int:team_id>', methods=['POST'])
@login_required
def team_delete(team_id):
    team = Team.query.get_or_404(team_id)
    # Bağlı maçların fotoğrafları da silinsin
    related = Match.query.filter(
        (Match.team1_id == team_id) | (Match.team2_id == team_id)
    ).all()
    for m in related:
        _delete_match_photo_dir(m.id)
    Match.query.filter(
        (Match.team1_id == team_id) | (Match.team2_id == team_id)
    ).delete(synchronize_session=False)
    db.session.delete(team)
    db.session.commit()
    flash(f'Takım "{team.name}" ve bağlı maçlar/fotoğraflar silindi.')
    return redirect(url_for('admin'))


def _delete_match_photo_dir(match_id):
    import shutil
    match_dir = UPLOADS_DIR / 'matches' / str(match_id)
    if match_dir.exists():
        shutil.rmtree(match_dir, ignore_errors=True)


# ---------- Admin: Matches ----------

@app.route('/admin/match_add', methods=['POST'])
@login_required
def match_add():
    try:
        t1_id = int(request.form.get('team1', 0))
        t2_id = int(request.form.get('team2', 0))
        t1_score = int(request.form.get('team1_score') or 0)
        t2_score = int(request.form.get('team2_score') or 0)
    except (TypeError, ValueError):
        flash('Geçersiz sayısal değer!')
        return redirect(url_for('admin'))

    if t1_score < 0 or t2_score < 0:
        flash('Skor negatif olamaz!')
        return redirect(url_for('admin'))

    if t1_id != t2_id and Team.query.get(t1_id) and Team.query.get(t2_id):
        match = Match(
            team1_id=t1_id, team2_id=t2_id,
            team1_score=t1_score, team2_score=t2_score
        )
        db.session.add(match)
        db.session.commit()
        flash('Maç eklendi.')
        return redirect(url_for('admin_match', match_id=match.id))
    flash('Geçersiz takımlar!')
    return redirect(url_for('admin'))


@app.route('/admin/match/<int:match_id>', methods=['GET'])
@login_required
def admin_match(match_id):
    """Tek bir maçın admin görünümü: skor düzenle, fotoğraf yükle/sil."""
    match = Match.query.get_or_404(match_id)
    return render_template('admin_match.html', match=match,
                           max_photos=MAX_PHOTOS_PER_MATCH)


@app.route('/admin/match_update/<int:match_id>', methods=['POST'])
@login_required
def match_update(match_id):
    match = Match.query.get_or_404(match_id)
    try:
        t1 = int(request.form.get('team1_score') or 0)
        t2 = int(request.form.get('team2_score') or 0)
    except (TypeError, ValueError):
        flash('Geçersiz skor!')
        return redirect(url_for('admin_match', match_id=match_id))
    if t1 < 0 or t2 < 0:
        flash('Skor negatif olamaz!')
        return redirect(url_for('admin_match', match_id=match_id))
    match.team1_score = t1
    match.team2_score = t2
    match.notes = request.form.get('notes', '').strip()[:2000]
    db.session.commit()
    flash('Maç güncellendi.')
    return redirect(url_for('admin_match', match_id=match_id))


@app.route('/admin/match_delete/<int:match_id>', methods=['POST'])
@login_required
def match_delete(match_id):
    match = Match.query.get_or_404(match_id)
    _delete_match_photo_dir(match_id)
    db.session.delete(match)
    db.session.commit()
    flash('Maç ve fotoğrafları silindi.')
    return redirect(url_for('admin'))


# ---------- Admin: Photos ----------

@app.route('/admin/match/<int:match_id>/photo_upload', methods=['POST'])
@login_required
def photo_upload(match_id):
    match = Match.query.get_or_404(match_id)

    existing = MatchPhoto.query.filter_by(match_id=match_id).count()
    files = request.files.getlist('photos')

    if not files or (len(files) == 1 and not files[0].filename):
        flash('Fotoğraf seçilmedi.')
        return redirect(url_for('admin_match', match_id=match_id))

    caption = request.form.get('caption', '').strip()[:250]
    uploaded = 0
    skipped = 0

    for f in files:
        if existing + uploaded >= MAX_PHOTOS_PER_MATCH:
            skipped += 1
            continue
        if not _allowed_file(f.filename):
            skipped += 1
            continue
        name = _save_photo(f, match_id)
        if name:
            db.session.add(MatchPhoto(
                match_id=match_id, filename=name, caption=caption
            ))
            uploaded += 1
        else:
            skipped += 1

    db.session.commit()
    msg = f'{uploaded} fotoğraf yüklendi.'
    if skipped:
        msg += f' ({skipped} tanesi atlandı — izinli format değil veya limit aşıldı.)'
    flash(msg)
    return redirect(url_for('admin_match', match_id=match_id))


@app.route('/admin/photo_delete/<int:photo_id>', methods=['POST'])
@login_required
def photo_delete(photo_id):
    photo = MatchPhoto.query.get_or_404(photo_id)
    match_id = photo.match_id
    _delete_photo_files(match_id, photo.filename)
    db.session.delete(photo)
    db.session.commit()
    flash('Fotoğraf silindi.')
    return redirect(url_for('admin_match', match_id=match_id))


# ---------- Bootstrap ----------

def _ensure_schema():
    """Şema uyumsuzluğu varsa DB'yi yeniden oluştur (lokal dev için)."""
    from sqlalchemy import inspect
    insp = inspect(db.engine)
    if 'match' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('match')]
        if 'home_team_id' in cols or 'away_team_id' in cols:
            print("Eski ev/deplasman şeması tespit edildi — DB yeniden oluşturuluyor...")
            db.drop_all()
    db.create_all()


with app.app_context():
    _ensure_schema()


if __name__ == '__main__':
    app.run(debug=True)
