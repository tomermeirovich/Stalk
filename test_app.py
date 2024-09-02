import pytest
from app import app, db
from models import User, Post, Like, Dislike, Friend
import io
from flask import url_for

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test_secret_key'
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_index_redirect(client):
    response = client.get('/')
    assert response.status_code == 302
    assert response.location == '/login'

def test_login(client):
    # First, register a user
    client.post('/register', data={
        'username': 'testuser',
        'password': 'testpassword',
        'profile_picture': (io.BytesIO(b"abcdef"), 'test.jpg')
    })

    # Then, try to login
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpassword'
    })
    print(f"Login response: {response.data}")
    assert response.status_code == 302
    assert response.location == url_for('index')

    with client.session_transaction() as session:
        assert session['user_id'] is not None

def test_post(client):
    # Register and login
    client.post('/register', data={
        'username': 'testuser',
        'password': 'testpassword',
        'profile_picture': (io.BytesIO(b"abcdef"), 'test.jpg')
    })
    client.post('/login', data={'username': 'testuser', 'password': 'testpassword'})
    
    response = client.post('/post', data={'content': 'Hello, world!'})
    assert response.status_code == 302
    assert response.location == url_for('index')

    post = Post.query.first()
    assert post is not None
    assert post.content == 'Hello, world!'
    assert post.user.username == 'testuser'

def test_like_post(client):
    # Register and login
    client.post('/register', data={
        'username': 'testuser',
        'password': 'testpassword',
        'profile_picture': (io.BytesIO(b"abcdef"), 'test.jpg')
    })
    client.post('/login', data={'username': 'testuser', 'password': 'testpassword'})
    
    # Create a post
    client.post('/post', data={'content': 'Test post'})
    post = Post.query.first()
    
    response = client.post(f'/like/{post.id}')
    print(f"Response status code: {response.status_code}")
    print(f"Response location: {response.location}")

    like = Like.query.filter_by(post_id=post.id).first()
    print(f"Like object: {like}")
    if like is None:
        print("Likes in database:")
        print(Like.query.all())

    assert like is not None
    assert like.user.username == 'testuser'
    assert like.post.content == 'Test post'

def test_dislike_post(client):
    # Register and login
    client.post('/register', data={
        'username': 'testuser',
        'password': 'testpassword'
    })
    client.post('/login', data={'username': 'testuser', 'password': 'testpassword'})
    
    # Create a post
    client.post('/post', data={'content': 'Test post'})
    
    post = Post.query.first()
    assert post is not None, "Post was not created"

    response = client.post(f'/dislike/{post.id}')
    assert response.status_code == 302
    assert response.location == url_for('index')

def test_logout(client):
    # Register and login
    client.post('/register', data={
        'username': 'testuser',
        'password': 'testpassword'
    })
    client.post('/login', data={'username': 'testuser', 'password': 'testpassword'})
    
    response = client.get('/logout')
    assert response.status_code == 302
    assert response.location == '/login'

    with client.session_transaction() as session:
        assert 'user_id' not in session

def test_index_with_posts(client):
    # Register and log in
    client.post('/register', data={
        'username': 'testuser',
        'password': 'testpassword',
        'profile_picture': (io.BytesIO(b"abcdef"), 'test.jpg')
    })
    login_response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpassword'
    })
    print(f"Login response: {login_response.data}")
    assert login_response.status_code == 302

    # Create posts
    client.post('/post', data={'content': 'Test post 1'})
    client.post('/post', data={'content': 'Test post 2'})

    # Get the index page and follow redirects
    response = client.get('/', follow_redirects=True)

    assert response.status_code == 200
    # Add more assertions to check the content of the page