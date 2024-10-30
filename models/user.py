from flask import Flask, request, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from threading import Thread
from time import sleep
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()


app = Flask(__name__)
# postgresql://username:password@host:port/dbname
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

'''
Code based on microservice-VM git repository, containing User(db.Model) and functions.
'''

# User model with common user attributes
class User(db.Model):
    __tablename__ = 'users'
     
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

    def serialize(self):
        return {'id': self.id, 'username': self.username, 'email': self.email}

with app.app_context():
    db.create_all()

# Get all users with pagination and username filter
@app.route('/api/users', methods=['GET'])
def get_users():

    # Query String with parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    username_filter = request.args.get('username', None)

    query = User.query
    if username_filter:
        query = query.filter(User.username.ilike(f'%{username_filter}%'))

    users = query.paginate(page=page, per_page=per_page, error_out=False)
    response = {
        'users': [user.serialize() for user in users.items],
        'total': users.total,
        'pages': users.pages
    }

    return jsonify(response), 200, {
        'Link': f'<{url_for("get_users", page=page+1, per_page=per_page, _external=True)}>; rel="next"'
    }

# Create a new user
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.json
    if 'username' not in data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Bad request, missing required fields'}), 400

    new_user = User(username=data['username'], email=data['email'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()

    # 201 Created with a link header for a POST
    location = url_for('get_user', user_id=new_user.id, _external=True)
    return jsonify({'message': 'User created!'}), 201, {'Location': location}

# Get a specific user by ID
@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.serialize())

def async_update(user, email):
    sleep(5)
    # Update a user's email (or another attribute if needed) asynchronously
    user.email = email
    db.session.commit()

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json

    if 'email' not in data:
        return jsonify({'error': 'Bad request, missing email field'}), 400

    thread = Thread(target=async_update, args=(user, data['email']))
    thread.start()

    return jsonify({'message': 'User update accepted'}), 202

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'}), 204

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({'error': 'Bad request'}), 400


# Example routes
@app.route('/')
def index():
    return jsonify({"message": "Welcome to our food rating app!"}), 200

@app.route('/data', methods=['GET'])
def get_data():
    return jsonify({"message": "Data retrieved successfully"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0')