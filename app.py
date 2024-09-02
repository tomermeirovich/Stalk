import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from models import db, User, Post, Like, Dislike, Comment, Friend
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def root():
    if 'user_id' in session and session.get('remember_me', False):
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def index():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    for post in posts:
        post.like_count = post.likes.count()
        post.dislike_count = post.dislikes.count()
        post.comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.timestamp.desc()).all()
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
            flash('שם המשתמש כבר קיים. אנ בחר שם משתמש אחר.', 'error')
            return redirect(url_for('register'))

        user = User(username=username, profile_picture=filename)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user, remember=True)
        flash('נרשמת והתחברת בהצלחה!', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            session['user_id'] = user.id
            flash('התחברת בהצלחה!', 'success')
            return redirect(url_for('index'))
        flash('שם משתמש או סיסמה לא נכונים', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    session.pop('user_id', None)
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
    like = Like(user_id=current_user.id, post_id=post_id)
    db.session.add(like)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/dislike/<int:post_id>', methods=['POST'])
@login_required
def dislike_post(post_id):
    # Your existing dislike logic here
    return redirect(url_for('index'))

@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content')
    if content:
        comment = Comment(content=content, user_id=current_user.id, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        flash('התגובה נוספה בהצלחה!', 'success')
    return redirect(url_for('index'))

@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    user = User.query.get_or_404(user_id)
    likes_count = Like.query.filter_by(user_id=user.id).count()
    dislikes_count = Dislike.query.filter_by(user_id=user.id).count()
    return render_template('profile.html', user=user, likes_count=likes_count, dislikes_count=dislikes_count)

@app.route('/add_friend/<int:friend_id>', methods=['POST'])
@login_required
def add_friend(friend_id):
    existing_friend = Friend.query.filter_by(user_id=current_user.id, friend_id=friend_id).first()
    if not existing_friend:
        friend = Friend(user_id=current_user.id, friend_id=friend_id)
        db.session.add(friend)
        db.session.commit()
        flash('החבר נוסף בהצלחה!', 'success')
    else:
        flash('החבר כבר קיים ברשימה.', 'error')
    return redirect(url_for('profile', user_id=friend_id))

@app.route('/remove_friend/<int:friend_id>', methods=['POST'])
@login_required
def remove_friend(friend_id):
    friend = Friend.query.filter_by(user_id=current_user.id, friend_id=friend_id).first()
    if friend:
        db.session.delete(friend)
        db.session.commit()
        flash('החבר הוסר בהצלחה!', 'success')
    else:
        flash('החבר לא נמצא ברשימה.', 'error')
    return redirect(url_for('profile', user_id=friend_id))

@app.route('/search', methods=['GET'])
@login_required
def search_users():
    query = request.args.get('query', '')
    users = User.query.filter(User.username.ilike(f'%{query}%')).all()
    return render_template('search_results.html', users=users, query=query)

@app.route('/like_comment/<int:comment_id>', methods=['POST'])
@login_required
def like_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    like = Like(user_id=current_user.id, comment_id=comment_id)
    db.session.add(like)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/dislike_comment/<int:comment_id>', methods=['POST'])
@login_required
def dislike_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    dislike = Dislike(user_id=current_user.id, comment_id=comment_id)
    db.session.add(dislike)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
