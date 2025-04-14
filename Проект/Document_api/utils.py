from flask import request, jsonify
from functools import wraps
from .models import Users
from . import db

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not auth.username or not auth.password:
            return jsonify({'message': 'Authentication required'}), 401

        user = Users.query.filter_by(username=auth.username).first()
        if not user or not user.check_password(auth.password):
            return jsonify({'message': 'Invalid credentials'}), 401

        return f(*args, **kwargs)

    return decorated
