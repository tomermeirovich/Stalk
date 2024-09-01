import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from models import db, User, Post, Like, Dislike, Comment # Import models from models.py
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db.init_app(app)  # Initialize db with the app
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Remove the User and Post model definitions from here

# Rest of your routes and app logic remain the same

@app.route('/')
def root():
    if 'user_id' in session and session.get('remember_me', False):
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def index():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('index.html', posts=posts, user=current_user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        profile_picture = request.files.get('profile_picture')

        if profile_picture and profile_picture.filename != '':
            filename = secure_filename(profile_picture.filename)
            profile_picture.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = 'default_frog.png'

        if User.query.filter_by(username=username).first():
            flash('שם המשתמש כבר קיים. אנא בחר שם משתמש אחר.', 'error')
            return redirect(url_for('register'))

        user = User(username=username, profile_picture=filename)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Log in the user immediately after registration
        login_user(user)
        flash('נרשמת והתחברת בהצלחה!', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember_me = 'remember_me' in request.form
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=remember_me)
            session['user_id'] = user.id  # Add this line
            flash('התחברת בהצלחה!', 'success')
            return redirect(url_for('index'))
        else:
            flash('שם משתמש או סיסמה לא נכונים.', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)  # Add this line to remove user_id from session
    flash('התנתקת בהצלחה.', 'success')
    return redirect(url_for('login'))

@app.route('/post', methods=['POST'])
@login_required
def post():
    content = request.form['content']
    post = Post(content=content, user_id=current_user.id)
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    existing_like = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    existing_dislike = Dislike.query.filter_by(user_id=current_user.id, post_id=post.id).first()

    if existing_dislike:
        db.session.delete(existing_dislike)

    if existing_like:
        db.session.delete(existing_like)
    else:
        like = Like(user_id=current_user.id, post_id=post.id)
        db.session.add(like)

    db.session.commit()
    return redirect(url_for('index'))

@app.route('/dislike/<int:post_id>', methods=['POST'])
@login_required
def dislike_post(post_id):
    post = Post.query.get_or_404(post_id)
    existing_like = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    existing_dislike = Dislike.query.filter_by(user_id=current_user.id, post_id=post.id).first()

    if existing_like:
        db.session.delete(existing_like)

    if existing_dislike:
        db.session.delete(existing_dislike)
    else:
        dislike = Dislike(user_id=current_user.id, post_id=post.id)
        db.session.add(dislike)

    db.session.commit()
    return redirect(url_for('index'))

@app.route('/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    content = request.form['content']
    user_id = session['user_id']
    comment = Comment(content=content, user_id=user_id, post_id=post_id)
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
