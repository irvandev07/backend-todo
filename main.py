from crypt import methods
from datetime import datetime, timedelta
from email.mime import image
from functools import wraps
import queue
import token
from flask import Flask, jsonify, make_response, request
from flask_sqlalchemy import SQLAlchemy
import uuid
import base64
import jwt
from flask_cors import CORS, cross_origin

app = Flask(__name__)
db = SQLAlchemy(app)
CORS(app, supports_credentials=True)

app.config['SECRET_KEY'] = 'your secret key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Sychrldi227@localhost:5432/db_todos'


class User(db.Model):
	id = db.Column(db.Integer, primary_key=True, index=True)
	name = db.Column(db.String(20), nullable=False)
	username = db.Column(db.String(28), nullable=False, unique=True)
	password = db.Column(db.String(28), nullable=False, unique=True)
	image = db.Column(db.String)
	public_id = db.Column(db.String, nullable=False)
	is_admin = db.Column(db.Boolean, default=False)
	todos = db.relationship('Todo', backref='owner', lazy='dynamic')

	def __repr__(self):
		return f'User <{self.email}>'


class Todo(db.Model):
	id = db.Column(db.Integer, primary_key=True, index=True)
	public_id = db.Column(db.String, nullable=False)
	name = db.Column(db.String(100), nullable=False)
	tags = db.Column(db.String(100))
	description = db.Column(db.Text, nullable=False)
	is_completed = db.Column(db.Boolean, default=False)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

	def __repr__(self):
		return f'Todo: <{self.name}>'


# assoc_table = db.Table('shared_todo_user', db.Model.metadata,
#     db.Column('shared_todo_id', db.ForeignKey(
#         'shared_todo.id'), primary_key=True),
#     db.Column('member_id', db.ForeignKey('user.id'), primary_key=True)
# )


# class SharedTodo(db.Model):
#   id = db.Column(db.Integer, primary_key=True, index=True)
#   name = db.Column(db.String(1024), nullable=False)
#   is_completed = db.Column(db.Boolean, default=False)
#   public_id = db.Column(db.String, nullable=False)
#   members = db.relationship(
#       'User', secondary=assoc_table, backref="shared_todos")

#   def __repr__(self):
#     return f'SharedTodo: <{self.name}>'


# generate database schema on startup, if not exists:
# db.create_all()
# db.session.commit()


# @app.route('/')
# def home():
#   result = db.engine.execute('SELECT name, email FROM public.user')
#   for r in result:
#     print(r)
#     print(type(r))
#     print('email:', r['email'])
#   return {
#     'message': 'Welcome to building RESTful APIs with Flask and SQLAlchemy'
#   }

def token_required(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		token = None
		if 'x-access-token' in request.headers:
				token = request.headers['x-access-token']
		if not token:
				return jsonify({'message' : 'Token is missing !!'}), 401
		try:
				data = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")
				current_user = User.query.filter_by(username=data['username']).first()
		except:
				return jsonify({
						'message' : 'Token is invalid !!'
				}), 401
		return  f(current_user, *args, **kwargs)
	return decorated
		

@app.route('/login/' , methods=['POST'])
@cross_origin(supports_credentials=True)
def author_user():
	decode_var = request.headers.get('Authorization')
	c = base64.b64decode(decode_var[6:])
	e = c.decode("ascii")
	lis = e.split(':')
	username = lis[0]
	passw = lis [1]
	user = User.query.filter_by(username=username).filter_by(password=passw).first()

	if not user:
		return make_response(
				'Please check login detail'
		),401
	elif user:
		token = jwt.encode({
						'username': user.username, 'image' : user.image,
						'exp' : datetime.utcnow() + timedelta(hours = 48)
		}, app.config['SECRET_KEY'])
		return make_response(jsonify({'token' : token}), 201)

#jwt.decode(token,app.config['SECRET_KEY'],algorithms=["HS256"]

@app.route('/users/')
def get_users():
	return jsonify([
		{
			'id': user.public_id, 'name': user.name, 'email': user.username,
			'is admin': user.is_admin
			} for user in User.query.all()
	])


# @app.route('/users/<id>/')
# def get_user(id):
#     print(id)
#     user = User.query.filter_by(public_id=id).first_or_404()
#     return {
#       'id': user.public_id, 'name': user.name,
#       'email': user.email, 'is_admin': user.is_admin,
#       'todos': [t.name for t in user.todos]
#       }


@app.route('/users/', methods=['POST'])
@cross_origin()
def create_user():
	data = request.get_json()
	if not 'name' in data or not 'username' in data:
		return jsonify({
			'error': 'Bad Request',
			'message': 'Name or email not given'
		}), 400
	if len(data['name']) < 4 or len(data['username']) < 4:
		return jsonify({
			'error': 'Bad Request',
			'message': 'Name and email must be contain minimum of 4 letters'
		}), 400
	# user = User.query.filter_by(username=data['username']).first()
	u = User(
			username=data['username'],
			password=data['password'],
			name=data['name'],
			image = "https://i.postimg.cc/SKBWJh99/user.png",
			is_admin=data.get('is admin', False),
			public_id=str(uuid.uuid4())
		)
	db.session.add(u)
	db.session.commit()
	return {
		'id': u.public_id, 'name': u.name,
		'username': u.username, 'is admin': u.is_admin
	}, 201


# @app.route('/users/<id>/', methods=['PUT'])
# def update_user(id):
#   data = request.get_json()
#   if 'name' not in data:
#     return {
#       'error': 'Bad Request',
#       'message': 'Name field needs to be present'
#     }, 400
#   user = User.query.filter_by(public_id=id).first_or_404()
#   user.name = data['name']
#   if 'is admin' in data:
#     user.is_admin = data['admin']
#   db.session.commit()
#   return jsonify({
#     'id': user.public_id,
#     'name': user.name, 'is admin': user.is_admin,
#     'email': user.email
#     })


# @app.route('/users/<id>/', methods=['DELETE'])
# def delete_user(id):
#   user = User.query.filter_by(public_id=id).first_or_404()
#   db.session.delete(user)
#   db.session.commit()
#   return {
#     'success': 'Data deleted successfully'
#   }
	


@app.route('/todos/')
@token_required
def get_todos(current_user):
	return jsonify([
		{ 
			'id': todo.id, 
			'name': todo.name,
			'tags' : todo.tags,
			'description' : todo.description,
			'is_completed': todo.is_completed,
			'owner': {
				'name': todo.owner.name,
				'username': todo.owner.username,
				'public_id': todo.owner.public_id
			}
		} for todo in Todo.query.filter_by(user_id=current_user.id).all()
	])

@app.route('/search-todo/', methods=['POST'])
@cross_origin()
def search_product():
		lis =[]
		data = request.get_json()
		pro = data['name']
		search = "%{}%".format(pro)
		todos = Todo.query.filter(Todo.name.ilike(search)).all()
		if not todos:
			lis.append ({'message' : 'Did not find search'})
			return jsonify(lis),404
		else:
			for x in todos:
					lis.append(
						{
							'id': x.id, 
							'name': x.name,
							'tags': x.tags,
							'description': x.description,
							'is_completed': x.is_completed
						} 
					)
			return jsonify(lis), 200

@app.route('/todos/<id>')
def get_todo(id):
	todo = Todo.query.filter_by(id=id).first_or_404()
	return jsonify({ 
			'id': todo.id, 'name': todo.name,'description' : todo.description,
		#   'owner': {
		#     'name': todo.owner.name,
		#     'email': todo.owner.email,
		#     'public_id': todo.owner.public_id
		#   }
		})

@app.route('/todos/', methods=['POST'])
@token_required
@cross_origin(supports_credentials=True)
def create_todo(current_user):
	data = request.get_json()
#   if not 'name' in data or not 'email' in data:
#     return jsonify({
#       'error': 'Bad Request',
#       'message': 'Name of todo or email of creator not given'
#     }), 400
	if len(data['name']) < 4:
		return jsonify({
			'error': 'Bad Request',
			'message': 'Name of todo contain minimum of 4 letters'
		}), 400

	# user=User.query.filter_by(username=data['username']).first()
	if not current_user:
		return {
			'error': 'Bad request',
			'message': 'Invalid email, no user with that email'
		}
	is_completed = data.get('is completed', False)
	todo = Todo(
		name=data['name'], 
		tags= data['tags'], 
		user_id=current_user.id,
		description=data["description"],
		is_completed=is_completed, 
		public_id=str(uuid.uuid4())
	)
	db.session.add(todo)
	db.session.commit()
	return {
		'id': todo.public_id, 
		'name': todo.name, 
		'description' : todo.description,
		'completed': todo.is_completed,
		'owner': {
			'name': todo.owner.name,
			'username': todo.owner.username,
			'is admin': todo.owner.is_admin 
		} 
	}, 201

@app.route('/todos/<id>/', methods=['PUT'])
@cross_origin()
def update_todo(id):
		data = request.get_json()
		todo = Todo.query.filter_by(id=id).first()
		todo.is_completed=data['is completed']
		db.session.commit()
		return {
			'id': todo.public_id, 'name': todo.name, 'description' : todo.description,
			'is completed': todo.is_completed
}, 201

@app.route('/todos/data/<id>/', methods=['PUT'])
@cross_origin()
def update_data_todo(id):
		data = request.get_json()
		todo = Todo.query.filter_by(id=id).first_or_404()
		todo.name = data['name']
		todo.tags = data['tags']
		if 'image' in data:
			todo.image = data['image']
		todo.description = data['description']
		db.session.commit()
		return {
			'id': todo.public_id, 'name': todo.name, 'description' : todo.description,
			'is completed': todo.is_completed,
			# 'owner': {
			#   'name': todo.owner.name, 'email': todo.owner.email,
			#   'is admin': todo.owner.is_admin 
			# } 
}, 201

@app.route('/todos/<id>/', methods=['DELETE'] )
def delete_todo(id):
	todo = Todo.query.filter_by(id=id).first_or_404()
	db.session.delete(todo)
	db.session.commit()
	return {
		'success': 'Data deleted successfully'
	}

# @app.route('/shared-todos/')
# def get_shared_todos():
#   return jsonify([
#     { 
#       'id': shared_todo.public_id, 'name': shared_todo.name,
#       'members': [{
#         'name': member.name,
#         'email': member.email,
#         'public_id': member.public_id
#       } for member in shared_todo.members]
#     } for shared_todo in SharedTodo.query.all()
#   ])

# @app.route('/shared-todos/', methods=['POST'])
# def create_shared_todos():
#   data = request.get_json()
#   if not 'name' in data or not 'email' in data:
#     return jsonify({
#       'error': 'Bad Request',
#       'message': 'Name of todo or id of owners not given'
#     }), 400

#   todo = SharedTodo(
#     name=data['name'], is_completed=False, public_id=str(uuid.uuid4())
#   )
#   user=User.query.filter_by(email=data['email']).first()
#   if not user:
#     return {
#       'error': 'Bad request',
#       'message': 'Invalid email, no user with that email'
#     }

#   todo.members.append(user)
#   db.session.add(todo)
#   db.session.commit()
#   return jsonify([
#     { 
#       'id': todo.id
#     }
#   ])

if __name__ == '__main__':
	app.run()