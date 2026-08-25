import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, Player, Team, AuctionLog
from werkzeug.utils import secure_filename
from datetime import datetime
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from flask_migrate import Migrate
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)
print("Using Cloudinary cloud name:", cloudinary.config().cloud_name)
#
# import cloudinary
# import cloudinary.uploader
#
# cloudinary.config(
#     url=os.environ.get('CLOUDINARY_URL')
# )
# DATABASE_URI = os.environ.get('DATABASE_URI')
# app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db.init_app(app)
# migrate = Migrate(app, db)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///auction.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
# Upload folder for local images
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Create tables
with app.app_context():
    db.create_all()

# ------------------- ROUTES -------------------

@app.route('/')
def index():
    return render_template('index.html')

# 1. Player Registration
@app.route('/register-player', methods=['GET', 'POST'])
def register_player():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        batting_style = request.form.get('batting_style', '')
        bowling_style = request.form.get('bowling_style', '')

        # Normalize based on role
        if role in ['Batsman', 'Wicketkeeper']:
            bowling_style = None
        elif role == 'Bowler':
            batting_style = None
        # All-rounder keeps both

        # Image upload
        # image = request.files['image']
        # if image and allowed_file(image.filename):
        #     filename = secure_filename(image.filename)
        #     unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        #     filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        #     image.save(filepath)
        #     image_path = f"/{filepath}"
        # else:
        #     image_path = None
        image = request.files.get('image')
        image_url = None
        if image and allowed_file(image.filename):
            try:
                upload_result = cloudinary.uploader.upload(image, folder="city_club/players")
                image_url = upload_result['secure_url']
            except Exception as e:
                flash(f'Image upload failed: {e}', 'error')

        player = Player(
            name=name,
            role=role,
            age=0,                        # default, not used
            nationality='Not specified',  # default
            batting_style=batting_style,
            bowling_style=bowling_style,
            image_path=image_url
        )
        db.session.add(player)
        db.session.commit()

        flash(f'Player {name} registered successfully! ID: {player.id}', 'success')
        return render_template('player_confirmation.html', player=player)

    return render_template('register_player.html')

# 2. Team Registration
@app.route('/register-team', methods=['GET', 'POST'])
def register_team():
    if request.method == 'POST':
        team_name = request.form['team_name']
        owner = request.form['owner']
        logo = request.files['logo']

        # if logo and allowed_file(logo.filename):
        #     filename = secure_filename(logo.filename)
        #     unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        #     filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        #     logo.save(filepath)
        #     logo_path = f"/{filepath}"
        # else:
        #     logo_path = None
        logo = request.files.get('logo')
        logo_url = None
        if logo and allowed_file(logo.filename):
            try:
                upload_result = cloudinary.uploader.upload(logo, folder="city_club/teams")
                logo_url = upload_result['secure_url']
            except Exception as e:
                flash(f'Logo upload failed: {e}', 'error')

        team = Team(name=team_name, owner=owner, logo_path=logo_url, remaining_funds=0)
        db.session.add(team)
        db.session.commit()

        flash(f'Team {team_name} registered successfully!', 'success')
        return redirect(url_for('register_team'))

    return render_template('register_team.html')

# 3. Fund Assignment (assign equal funds to all teams)
@app.route('/assign-funds', methods=['GET', 'POST'])
def assign_funds():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        teams = Team.query.all()
        if not teams:
            flash('No teams available. Please register a team first.', 'warning')
        else:
            for team in teams:
                team.remaining_funds = amount
            db.session.commit()
            flash(f'Successfully assigned {amount} to each team.', 'success')
        return redirect(url_for('assign_funds'))

    teams = Team.query.all()
    return render_template('assign_funds.html', teams=teams)

# 4. Auction Page
@app.route('/auction', methods=['GET', 'POST'])
def auction():
    if request.method == 'POST':
        player_id = request.form.get('player_id')
        team_id = request.form.get('team_id')
        sold_price = float(request.form['sold_price'])

        player = Player.query.get(player_id)
        if not player:
            flash('Player not found.', 'error')
            return redirect(url_for('auction'))

        if player.sold:
            flash('Player is already sold!', 'error')
            return redirect(url_for('auction'))

        team = Team.query.get(team_id)
        if not team:
            flash('Invalid team selected.', 'error')
            return redirect(url_for('auction'))

        if team.remaining_funds < sold_price:
            flash(f'Insufficient funds for {team.name}. Available: {team.remaining_funds}', 'error')
            return redirect(url_for('auction'))

        # Deduct funds and mark player sold
        team.remaining_funds -= sold_price
        player.sold = True
        player.team_id = team.id
        player.sold_price = sold_price

        # Log auction
        log = AuctionLog(player_id=player.id, team_id=team.id, sold_price=sold_price)
        db.session.add(log)
        db.session.commit()

        flash(f'{player.name} sold to {team.name} for {sold_price}!', 'success')
        return redirect(url_for('auction') + '?sold=1')

    # GET: show search form
    player = None
    search_id = request.args.get('search_id')
    if search_id:
        player = Player.query.get(search_id)

    teams = Team.query.all()
    return render_template('auction.html', player=player, teams=teams)

# Dashboard
@app.route('/dashboard')
def dashboard():
    players = Player.query.all()
    teams = Team.query.all()
    logs = AuctionLog.query.order_by(AuctionLog.timestamp.desc()).limit(20).all()
    return render_template('dashboard.html', players=players, teams=teams, logs=logs)

# Teams listing
@app.route('/teams')
def teams():
    teams = Team.query.all()
    return render_template('teams.html', teams=teams)

# Team details
@app.route('/team/<int:team_id>')
def team_details(team_id):
    team = Team.query.get_or_404(team_id)
    players = Player.query.filter_by(team_id=team_id, sold=True).all()
    return render_template('team_details.html', team=team, players=players)

# Edit Player (single definition)
@app.route('/edit_player/<int:player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    if request.method == 'POST':
        try:
            player.name = request.form['name']
            player.role = request.form['role']
            player.batting_style = request.form.get('batting_style') or None
            player.bowling_style = request.form.get('bowling_style') or None

            image = request.files.get('image')
            if image and allowed_file(image.filename):
                try:
                    upload_result = cloudinary.uploader.upload(image, folder="city_club/players")
                    player.image_path = upload_result['secure_url']
                except Exception as e:
                    flash(f'Image upload failed: {e}', 'error')
                    # Continue with old image

            db.session.commit()
            flash(f'Player {player.name} updated successfully!', 'success')
            return redirect(request.referrer or url_for('players'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating player: {str(e)}', 'error')
            return redirect(url_for('edit_player', player_id=player.id))
    return render_template('edit_player.html', player=player)

# Delete Player (single definition)
@app.route('/delete_player/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    db.session.delete(player)
    db.session.commit()
    flash('Player deleted successfully!', 'success')
    return redirect(request.referrer or url_for('players'))

# Edit Team
@app.route('/edit_team/<int:team_id>', methods=['GET', 'POST'])
def edit_team(team_id):
    team = Team.query.get_or_404(team_id)
    if request.method == 'POST':
        team.name = request.form['team_name']
        team.owner = request.form['owner']
        logo = request.files.get('logo')
        # if logo and allowed_file(logo.filename):
        #     filename = secure_filename(logo.filename)
        #     unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        #     filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        #     logo.save(filepath)
        #     team.logo_path = f"/{filepath}"
        logo = request.files.get('logo')
        if logo and allowed_file(logo.filename):
            try:
                upload_result = cloudinary.uploader.upload(logo, folder="city_club/teams")
                team.logo_path = upload_result['secure_url']
            except Exception as e:
                flash(f'Logo upload failed: {e}', 'error')
        db.session.commit()
        flash(f'Team {team.name} updated successfully!', 'success')
        return redirect(url_for('teams'))
    return render_template('edit_team.html', team=team)

# Delete Team
@app.route('/delete_team/<int:team_id>', methods=['POST'])
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    # Release all players from this team
    players = Player.query.filter_by(team_id=team_id).all()
    for p in players:
        p.team_id = None
        p.sold = False
        p.sold_price = 0.0
    db.session.commit()
    db.session.delete(team)
    db.session.commit()
    flash(f'Team {team.name} deleted successfully. Players released.', 'success')
    return redirect(url_for('teams'))

# Players listing
@app.route('/players')
def players():
    all_players = Player.query.order_by(Player.id).all()
    return render_template('players.html', players=all_players)

if __name__ == '__main__':
    app.run(debug=True)