from flask import Flask, request, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from threading import Thread
from time import sleep


app = Flask(__name__)
# postgresql://username:password@host:port/dbname
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:hK(![9U*OON]FC}c[2r~1Fz|:VLx@microservice-2-database.chaomk0okau3.us-east-1.rds.amazonaws.com:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

'''
Following code snippets based on microservice-VM git repository,
We can modify the database model and functions as needed.
'''

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(200))

    def serialize(self):
        return {'id': self.id, 'name': self.name, 'description': self.description}


with app.app_context():
    db.create_all()

@app.route('/api/items', methods=['GET'])
def get_items():

    # Query String with parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    name_filter = request.args.get('name', None)

    query = Item.query
    if name_filter:
        query = query.filter(Item.name.ilike(f'%{name_filter}%'))

    items = query.paginate(page=page, per_page=per_page, error_out=False)
    response = {
        'items': [item.serialize() for item in items.items],
        'total': items.total,
        'pages': items.pages
    }

    # Implement GET on link header for created resource.
    return jsonify(response), 200, {
        'Link': f'<{url_for("get_items", page=page+1, per_page=per_page, _external=True)}>; rel="next"'
    }


@app.route('/api/items', methods=['POST'])
def create_item():
    data = request.json
    if 'name' not in data:
        return jsonify({'error': 'Bad request, missing name field'}), 400

    new_item = Item(name=data['name'], description=data.get('description', ''))
    db.session.add(new_item)
    db.session.commit()

    # 201 Created with a link header for a POST
    location = url_for('get_item', item_id=new_item.id, _external=True)
    return jsonify({'message': 'Item created!'}), 201, {'Location': location}


@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    item = Item.query.get_or_404(item_id)
    return jsonify(item.serialize())

def async_update(item, description):
    sleep(5)
    item.description = description
    db.session.commit()

@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    item = Item.query.get_or_404(item_id)
    data = request.json

    if 'description' not in data:
        return jsonify({'error': 'Bad request, missing description field'}), 400

    thread = Thread(target=async_update, args=(item, data['description']))
    thread.start()

    return jsonify({'message': 'Item update accepted'}), 202


@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Item deleted'}), 204


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({'error': 'Bad request'}), 400


# Example route
@app.route('/')
def index():
    return jsonify({"message": "Welcome to our food rating app!"}), 200

# Example route
@app.route('/data', methods=['GET'])
def get_data():
    # Placeholder function to interact with the database
    return jsonify({"message": "Data retrieved successfully"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0')
