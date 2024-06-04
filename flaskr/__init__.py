import logging
import os
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import redis
import json
import base64

redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_client = redis.StrictRedis(host='redis-service', port=6379, db=0, decode_responses=True)

app = Flask(__name__)
app.secret_key = 'supersecretkey'

logging.basicConfig(level=logging.DEBUG)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    if redis_client.hexists("users", user_id):
        return User(user_id)
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if redis_client.hexists("users", username):
            flash('Username already exists', 'error')
        else:
            password_hash = generate_password_hash(password)
            redis_client.hset("users", username, password_hash)
            flash('Registered successfully', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = redis_client.hget("users", username)
        if password_hash and check_password_hash(password_hash, password):
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/scrape', methods=['POST'])
@login_required
def scrape():
    try:
        num_pages = int(request.form['num_pages'])
        scraper_url = os.getenv('SCRAPER_URL', 'http://scraper-service:5001/trigger_scrape')
        response = requests.post(scraper_url, data={'num_pages': num_pages})
        response_data = response.json()

        if response_data.get('status') == 'success':
            scraped_anime_list = []
            for title, anime_json in redis_client.hgetall("anime").items():
                anime = json.loads(anime_json)
                if anime not in app.config.get('SCRAPED_ANIME_LIST', []):
                    scraped_anime_list.append(anime)

            app.config['SCRAPED_ANIME_LIST'] = scraped_anime_list 

            flash('Scraping completed successfully', 'success')
        else:
            flash('Scraping failed', 'error')

        return redirect(url_for('result', page=1))
    except Exception as e:
        logging.error("Error during scraping", exc_info=e)
        return str(e), 500

@app.route('/result', methods=['GET'])
def result():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 50
        sort_by = request.args.get('sort_by', 'title')
        sort_order = request.args.get('sort_order', 'asc')
        
        anime_list = []
        for title, anime_json in redis_client.hgetall("anime").items():
            anime_list.append(json.loads(anime_json))

        if sort_by and sort_order:
            reverse = (sort_order == 'desc')
            anime_list.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)

        start = (page - 1) * per_page
        end = start + per_page
        total_pages = (len(anime_list) - 1) // per_page + 1

        paginated_anime_list = anime_list[start:end]

        return render_template('result.html', anime_list=paginated_anime_list, page=page, total_pages=total_pages, sort_by=sort_by, sort_order=sort_order)
    except Exception as e:
        logging.error("Error during result display", exc_info=e)
        return str(e), 500



@app.route('/anime/<title>', methods=['GET'])
def anime_details(title):
    try:
        anime = None
        anime_list = app.config.get('ANIME_LIST', [])
        if anime_list:
            anime = next((anime for anime in anime_list if anime['title'] == title), None)

        if not anime:
            anime_json = redis_client.hget("anime", title)
            if anime_json:
                anime = json.loads(anime_json)

        if anime:
            return render_template('anime_details.html', anime=anime)
        else:
            return "Anime not found", 404
    except Exception as e:
        logging.error("Error during displaying anime details", exc_info=e)
        return str(e), 500

@app.route('/filter', methods=['POST'])
def filter():
    try:
        selected_genres = request.form.getlist('genres')
        logging.debug(f"Selected genres: {selected_genres}")

        anime_list = []
        for title, anime_json in redis_client.hgetall("anime").items():
            anime = json.loads(anime_json)
            if any(genre in anime['genres'] for genre in selected_genres):
                anime_list.append(anime)

        page = request.args.get('page', 1, type=int)
        per_page = 50
        total_pages = (len(anime_list) - 1) // per_page + 1
        start = (page - 1) * per_page
        end = start + per_page
        paginated_anime_list = anime_list[start:end]

        logging.debug(f"Filtered anime list: {anime_list}")

        return render_template('result.html', anime_list=paginated_anime_list, page=page, total_pages=total_pages, sort_by='title', sort_order='asc')
    except Exception as e:
        logging.error("Error during filtering", exc_info=e)
        return str(e), 500

    
    
    
@app.route('/search', methods=['POST'])
def search():
    try:
        search_query = request.form['search_query'].lower()
        logging.debug(f"Search query: {search_query}")

        anime_list = []
        for title, anime_json in redis_client.hgetall("anime").items():
            anime = json.loads(anime_json)
            if search_query in anime['title'].lower():
                anime_list.append(anime)

        page = request.args.get('page', 1, type=int)
        per_page = 50
        total_pages = (len(anime_list) - 1) // per_page + 1
        start = (page - 1) * per_page
        end = start + per_page
        paginated_anime_list = anime_list[start:end]

        logging.debug(f"Searched anime list: {anime_list}")

        return render_template('result.html', anime_list=paginated_anime_list, page=page, total_pages=total_pages, sort_by='title', sort_order='asc')
    except Exception as e:
        logging.error("Error during searching", exc_info=e)
        return str(e), 500

    


@app.route('/read', methods=['GET'])
def read_from_db():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 50
        start = (page - 1) * per_page
        end = start + per_page
        sort_by = request.args.get('sort_by', 'title')
        sort_order = request.args.get('sort_order', 'asc')

        anime_list = []
        for title, anime_json in redis_client.hgetall("anime").items():
            anime_list.append(json.loads(anime_json))

        if sort_by and sort_order:
            anime_list.sort(key=lambda x: x.get(sort_by, ''), reverse=(sort_order == 'desc'))

        total_pages = (len(anime_list) - 1) // per_page + 1
        paginated_anime_list = anime_list[start:end]

        return render_template('result.html', anime_list=paginated_anime_list, page=page, total_pages=total_pages, sort_by=sort_by, sort_order=sort_order)
    except Exception as e:
        logging.error("Error during reading from database", exc_info=e)
        return str(e), 500

@app.route('/clear', methods=['POST'])
def clear_db():
    try:
        redis_client.flushdb()
        return render_template('index.html')
    except Exception as e:
        logging.error("Error during clearing database", exc_info=e)
        return str(e), 500

@app.route('/add_to_list/<title>', methods=['POST'])
@login_required
def add_to_list(title):
    try:
        anime_json = redis_client.hget("anime", title)
        if anime_json:
            redis_client.sadd(f"user:{current_user.id}:list", title)
            flash(f'Anime {title} added to your list', 'success')
        else:
            flash(f'Anime {title} not found', 'error')
        return redirect(url_for('anime_details', title=title))
    except Exception as e:
        logging.error("Error during adding to list", exc_info=e)
        return str(e), 500

@app.route('/update_anime/<title>', methods=['POST'])
@login_required
def update_anime(title):
    try:
        rating = request.form.get('rating')
        status = request.form.get('status')
        
        user_anime_key = f"user:{current_user.id}:anime:{title}"
        user_anime_data = {
            'rating': rating,
            'status': status
        }
        
        redis_client.hmset(user_anime_key, user_anime_data)
        flash('Anime updated successfully', 'success')
        return redirect(url_for('anime_details', title=title))
    except Exception as e:
        logging.error("Error during updating anime", exc_info=e)
        return str(e), 500

@app.route('/my_list', methods=['GET'])
@login_required
def my_list():
    try:
        user_anime_titles = redis_client.smembers(f"user:{current_user.id}:list")
        anime_list = []
        for title in user_anime_titles:
            anime_json = redis_client.hget("anime", title)
            if anime_json:
                anime = json.loads(anime_json)
                user_anime_data = redis_client.hgetall(f"user:{current_user.id}:anime:{title}")
                anime.update(user_anime_data)
                anime_list.append(anime)

        return render_template('my_list.html', anime_list=anime_list)
    except Exception as e:
        logging.error("Error during retrieving user list", exc_info=e)
        return str(e), 500
    
@app.route('/profile', defaults={'username': None})
@app.route('/profile/<username>')
@login_required
def profile(username):
    if username is None:
        username = current_user.username
    try:
        if username != current_user.username:
            visibility = redis_client.hget(f"user:{username}:profile", "visibility")
            if visibility != 'public':
                return "This profile is private", 403

        user_anime_titles = redis_client.smembers(f"user:{username}:list")
        completed_count = 0
        watching_count = 0
        plan_to_watch_count = 0
        dropped_count = 0
        total_rating = 0
        rated_count = 0

        for title in user_anime_titles:
            user_anime_data = redis_client.hgetall(f"user:{username}:anime:{title}")
            status = user_anime_data.get('status')
            rating = user_anime_data.get('rating')

            if status == 'Completed':
                completed_count += 1
            elif status == 'Watching':
                watching_count += 1
            elif status == 'Plan to watch':
                plan_to_watch_count += 1
            elif status == 'Dropped':
                dropped_count += 1

            if rating:
                total_rating += float(rating)
                rated_count += 1

        average_rating = total_rating / rated_count if rated_count > 0 else 0
        profile_image = redis_client.hget(f"user:{username}:profile", "image")
        visibility = redis_client.hget(f"user:{username}:profile", "visibility")

        return render_template('profile.html', 
                               username=username,
                               completed_count=completed_count, 
                               watching_count=watching_count, 
                               plan_to_watch_count=plan_to_watch_count, 
                               dropped_count=dropped_count, 
                               average_rating=round(average_rating, 2),
                               profile_image=profile_image,
                               visibility=visibility)
    except Exception as e:
        logging.error("Error during retrieving profile data", exc_info=e)
        return str(e), 500
    
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/upload_profile_image', methods=['POST'])
@login_required
def upload_profile_image():
    if 'profile_image' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('profile'))

    file = request.files['profile_image']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('profile'))

    if file and allowed_file(file.filename):
        image_data = file.read()
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        redis_client.hset(f"user:{current_user.id}:profile", "image", encoded_image)
        flash('Profile image uploaded successfully', 'success')
        return redirect(url_for('profile'))
    else:
        flash('Invalid file type', 'error')
        return redirect(url_for('profile'))
    
@app.route('/update_visibility', methods=['POST'])
@login_required
def update_visibility():
    visibility = request.form.get('visibility')
    redis_client.hset(f"user:{current_user.id}:profile", "visibility", visibility)
    flash('Profile visibility updated successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/search_profiles', methods=['POST'])
def search_profiles():
    search_query = request.form['search_query'].strip().lower()
    profiles = []

    for user in redis_client.hkeys("users"):
        visibility = redis_client.hget(f"user:{user}:profile", "visibility")
        if visibility == 'public':
            if search_query == "" or search_query in user.lower():
                profiles.append({"username": user})

    return render_template('search.html', profiles=profiles)

@app.route('/view_profile/<username>')
def view_profile(username):
    if not redis_client.hexists("users", username):
        return "User not found", 404

    visibility = redis_client.hget(f"user:{username}:profile", "visibility")
    if visibility != 'public':
        return "This profile is private", 403

    try:
        user_anime_titles = redis_client.smembers(f"user:{username}:list")
        completed_count = 0
        watching_count = 0
        plan_to_watch_count = 0
        dropped_count = 0
        total_rating = 0
        rated_count = 0

        for title in user_anime_titles:
            user_anime_data = redis_client.hgetall(f"user:{username}:anime:{title}")
            status = user_anime_data.get('status')
            rating = user_anime_data.get('rating')

            if status == 'Completed':
                completed_count += 1
            elif status == 'Watching':
                watching_count += 1
            elif status == 'Plan to watch':
                plan_to_watch_count += 1
            elif status == 'Dropped':
                dropped_count += 1

            if rating:
                total_rating += float(rating)
                rated_count += 1

        average_rating = total_rating / rated_count if rated_count > 0 else 0
        profile_image = redis_client.hget(f"user:{username}:profile", "image")

        return render_template('profile.html', 
                               username=username,
                               completed_count=completed_count, 
                               watching_count=watching_count, 
                               plan_to_watch_count=plan_to_watch_count, 
                               dropped_count=dropped_count, 
                               average_rating=round(average_rating, 2),
                               profile_image=profile_image,
                               visibility=visibility)
    except Exception as e:
        logging.error("Error during retrieving profile data", exc_info=e)
        return str(e), 500
    
@app.route('/anime_list/<username>')
def anime_list(username):
    try:
        visibility = redis_client.hget(f"user:{username}:profile", "visibility")
        if visibility != 'public' and username != current_user.username:
            return "This anime list is private", 403
        
        user_anime_titles = redis_client.smembers(f"user:{username}:list")
        anime_list = []

        for title in user_anime_titles:
            anime_json = redis_client.hget("anime", title)
            if anime_json:
                anime = json.loads(anime_json)
                user_anime_data = redis_client.hgetall(f"user:{username}:anime:{title}")
                anime.update(user_anime_data)
                anime_list.append(anime)

        return render_template('anime_list.html', anime_list=anime_list, username=username)
    except Exception as e:
        logging.error("Error during retrieving anime list", exc_info=e)
        return str(e), 500


if __name__ == "__main__":
    app.run(debug=True)
