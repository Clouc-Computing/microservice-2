from flask import Flask, request, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from threading import Thread
from time import sleep
import json
from dotenv import load_dotenv
import os
import boto3
import requests
# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
# postgresql://username:password@host:port/dbname
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
sns_client = boto3.client('sns', region_name=os.getenv('AWS_REGION'))

'''
Code based on microservice-VM git repository, containing Item(db.Model)
'''

class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(200))

    def serialize(self):
        return {'id': self.id, 'name': self.name, 'description': self.description}

class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    review = db.Column(db.String(200), nullable=False)
    rating = db.Column(db.Integer, nullable=False)

    def serialize(self):
        return {"id": self.id, "review": self.review, "rating": self.rating}

with app.app_context():
    db.create_all()

@app.route('/items', methods=['GET'])
def get_items():
    # Query String with parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 2, type=int)
    name_filter = request.args.get('name', None)

    query = Item.query
    if name_filter:
        query = query.filter(Item.name.ilike(f'%{name_filter}%'))

    items = query.paginate(page=page, per_page=per_page, error_out=False)

    # Generate HATEOS links for pagination
    links = {
        "self": url_for("get_items", page=page, per_page=per_page, _external=True),
        "next": url_for("get_items", page=page + 1, per_page=per_page, _external=True) if items.has_next else None,
        "prev": url_for("get_items", page=page - 1, per_page=per_page, _external=True) if items.has_prev else None,
    }

    response = {
        'items': [item.serialize() for item in items.items],
        'total': items.total,
        'pages': items.pages,
        '_links': links,
    }

    return jsonify(response), 200


@app.route('/items', methods=['POST'])
def create_item():
    data = request.json
    if 'name' not in data:
        return jsonify({'error': 'Bad request, missing name field'}), 400

    new_item = Item(name=data['name'], description=data.get('description', ''))
    db.session.add(new_item)
    db.session.commit()

    # Generate HATEOS links for the created item
    location = url_for('get_item', item_id=new_item.id, _external=True)
    links = {
        "self": location,
        "update": url_for('update_item', item_id=new_item.id, _external=True),
        "delete": url_for('delete_item', item_id=new_item.id, _external=True),
        "reviews": url_for('item_sub_resource', item_id=new_item.id, _external=True),
    }

    return jsonify({
        'id': new_item.id,
        'message': 'Item created!',
        '_links': links
    }), 201, {'Location': location}

@app.route('/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    item = Item.query.get_or_404(item_id)
    return jsonify(item.serialize())

def async_update(item, description):
    with app.app_context():  # Set up the application context
        print(f"Starting async update for item {item.id}")
        sleep(5)  # Simulate delay for the asynchronous operation
        item.description = description
        db.session.commit()
        print(f"Async update completed for item {item.id}")

@app.route('/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    item = Item.query.get_or_404(item_id)
    data = request.json

    if 'description' not in data:
        return jsonify({'error': 'Bad request, missing description field'}), 400

    thread = Thread(target=async_update, args=(item, data['description']))
    thread.start()

    return jsonify({'message': 'Item update accepted'}), 202


@app.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    Review.query.filter_by(item_id=item.id).delete()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Item deleted'}), 204

@app.route('/items/<int:item_id>/subResource', methods=['GET', 'POST'])
def item_sub_resource(item_id):
    item = Item.query.get_or_404(item_id)

    if request.method == 'GET':
        # Paginate subresources
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        reviews = Review.query.filter_by(item_id=item.id).paginate(page=page, per_page=per_page, error_out=False)
        links = {
            "self": url_for('item_sub_resource', item_id=item_id, page=page, per_page=per_page, _external=True),
            "next": url_for('item_sub_resource', item_id=item_id, page=page + 1, per_page=per_page, _external=True) if reviews.has_next else None,
            "prev": url_for('item_sub_resource', item_id=item_id, page=page - 1, per_page=per_page, _external=True) if reviews.has_prev else None,
        }

        response = {
            "item_id": item.id,
            "reviews": [review.serialize() for review in reviews.items],
            "total": reviews.total,
            "pages": reviews.pages,
            "_links": links,
        }

        return jsonify(response), 200

    elif request.method == 'POST':
        data = request.json
        if 'review' not in data or 'rating' not in data:
            return jsonify({"error": "Bad request, missing review or rating"}), 400

        new_review = Review(item_id=item.id, review=data['review'], rating=data['rating'])
        db.session.add(new_review)
        db.session.commit()

        try:
            notification_data = {
                "item_id": item.id,
                "review": data['review'],
                "rating": data['rating']
            }
            notification_url = "http://3.147.35.222:5002/notify"
            notification_response = requests.post(notification_url, json=notification_data)
            notification_response.raise_for_status() 
            print(f"Notification sent: {notification_response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send notification: {e}")

        return jsonify({"message": "Review created!", "review": new_review.serialize()}), 201
@app.route('/items/<int:item_id>/subResource/<int:review_id>', methods=['DELETE'])
def delete_review(item_id, review_id):
    # Ensure the item exists
    item = Item.query.get_or_404(item_id)

    # Ensure the review exists and is associated with the item
    review = Review.query.filter_by(id=review_id, item_id=item.id).first_or_404()

    # Delete the review
    db.session.delete(review)
    db.session.commit()

    return jsonify({"message": "Review deleted successfully!"}), 200
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({'error': 'Bad request'}), 400


# Example routes
@app.route('/')
def index():
    return jsonify({"message": "item database model"}), 200

@app.route('/data', methods=['GET'])
def get_data():
    # Placeholder function to interact with the database
    return jsonify({"message": "Data retrieved successfully"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
