from flask import Flask, request, jsonify, url_for, json
from flask_sqlalchemy import SQLAlchemy
from threading import Thread
from time import sleep
from dotenv import load_dotenv
import os
import boto3
import os

# Load environment variables from .env
load_dotenv()


app = Flask(__name__)
# postgresql://username:password@host:port/dbname
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
STEP_FUNCTION_ARN = os.getenv("STEP_FUNCTION_ARN")
step_functions_client = boto3.client('stepfunctions', region_name='us-east-2')
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

class FavoriteFood(db.Model):
    __tablename__ = 'favorite_foods'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    food_name = db.Column(db.String(80), nullable=False)

    def serialize(self):
        return {"id": self.id, "food_name": self.food_name}

with app.app_context():
    db.create_all()

@app.route('/users', methods=['GET'])
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
        'pages': users.pages,
        'current_page': page,
        'links': {
            'self': url_for('get_users', page=page, per_page=per_page, _external=True),
            'next': url_for('get_users', page=page + 1, per_page=per_page, _external=True) if users.has_next else None,
            'prev': url_for('get_users', page=page - 1, per_page=per_page, _external=True) if users.has_prev else None
        }
    }

    return jsonify(response), 200
def start_step_function(user_info):
    try:
        print("User info before serialization:", user_info)

        if isinstance(user_info, dict):
            input_json = json.dumps(user_info)
        else:
            raise ValueError("user_info must be a dictionary")

        print("Serialized input for Step Function:", input_json)

        response = step_functions_client.start_execution(
            stateMachineArn=STEP_FUNCTION_ARN,
            input=input_json  # Use the serialized JSON string
        )
        print(f"Step Function started: {response}")
    except Exception as e:
        print(f"Error starting Step Function: {e}")

# Create a new user
@app.route('/users', methods=['POST'])
def create_user():
    data = request.json
    if 'username' not in data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Bad request, missing required fields'}), 400

    new_user = User(username=data['username'], email=data['email'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()

    # 201 Created with a link header for a POST
    location = url_for('get_user', user_id=new_user.id, _external=True)
    # Log user creation in Step Function
    user_info = {
        "user_id": new_user.id,
        "username": new_user.username,
        "email": new_user.email
    }    
    Thread(target=start_step_function, args=(user_info,)).start()
    response = {
        'message': 'User created!',
        'user': new_user.serialize(),
        'links': {
            'self': location,
            'favorite_foods': url_for('user_sub_resource', user_id=new_user.id, _external=True)
        }
    }
    return jsonify(response), 201, {'Location': location}

# Get a specific user by ID with HATEOAS
@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    response = {
        'user': user.serialize(),
        'links': {
            'self': url_for('get_user', user_id=user_id, _external=True),
            'update': url_for('update_user', user_id=user_id, _external=True),
            'delete': url_for('delete_user', user_id=user_id, _external=True),
            'favorite_foods': url_for('user_sub_resource', user_id=user_id, _external=True)
        }
    }
    return jsonify(response), 200

# Get and add favorite foods for a user with pagination and HATEOAS
@app.route('/users/<int:user_id>/subResource', methods=['GET', 'POST'])
def user_sub_resource(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'GET':
        # Paginate favorite foods for the user
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        favorite_foods = FavoriteFood.query.filter_by(user_id=user.id).paginate(page=page, per_page=per_page, error_out=False)
        response = {
            "user_id": user.id,
            "favorite_foods": [food.serialize() for food in favorite_foods.items],
            "total": favorite_foods.total,
            "pages": favorite_foods.pages,
            "current_page": page,
            "links": {
                'self': url_for('user_sub_resource', user_id=user.id, page=page, per_page=per_page, _external=True),
                'next': url_for('user_sub_resource', user_id=user.id, page=page + 1, per_page=per_page, _external=True) if favorite_foods.has_next else None,
                'prev': url_for('user_sub_resource', user_id=user.id, page=page - 1, per_page=per_page, _external=True) if favorite_foods.has_prev else None
            }
        }
        return jsonify(response), 200

    elif request.method == 'POST':
        # Add a new favorite food
        data = request.json
        if 'food_name' not in data:
            return jsonify({"error": "Bad request, missing food_name"}), 400

        new_food = FavoriteFood(user_id=user.id, food_name=data['food_name'])
        db.session.add(new_food)
        db.session.commit()

        location = url_for('user_sub_resource', user_id=user.id, _external=True)
        response = {
            "message": "Favorite food added!",
            "food": new_food.serialize(),
            "links": {
                'self': location,
                'user': url_for('get_user', user_id=user.id, _external=True)
            }
        }
        return jsonify(response), 201, {'Location': location}


def async_update(user, email):
    with app.app_context():  # Ensure the application context is available
        print(f"Starting async update for user {user.id}")
        sleep(5)  # Simulate delay for the asynchronous operation
        user.email = email
        db.session.commit()
        print(f"Async update completed for user {user.id}")
@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json

    if 'email' not in data:
        return jsonify({'error': 'Bad request, missing email field'}), 400

    thread = Thread(target=async_update, args=(user, data['email']))
    thread.start()

    return jsonify({'message': 'User update accepted'}), 202

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    FavoriteFood.query.filter_by(user_id=user.id).delete()
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
    return jsonify({"message": "user database model"}), 200

@app.route('/data', methods=['GET'])
def get_data():
    return jsonify({"message": "Data retrieved successfully"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
