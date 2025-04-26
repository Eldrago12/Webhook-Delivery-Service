from flask import request, jsonify
from sqlalchemy.exc import IntegrityError
from . import api_bp
from ..database import db_session
from ..models import Subscription
from .schemas import subscription_schema, subscriptions_schema, subscription_create_update_schema, ValidationError
from ..cache import redis_client
from ..config import Config
import uuid
import json

def get_and_load_subscription_data(schema, partial=False):
    """Helper to handle request.json and Marshmallow loading."""
    if request.json is None:
        return None, {"message": "Request body must be valid JSON"}, 415

    errors = schema.validate(request.json)
    if errors:
        return None, {"errors": errors}, 400

    try:
        data = schema.load(request.json, partial=partial)
        return data, None, None
    except ValidationError as e:
        return None, {"errors": e.messages}, 400


@api_bp.route('/subscriptions', methods=['POST']) # type: ignore[reportReturnType]
def create_subscription():
    """Creates a new webhook subscription."""
    data, error_body, status_code = get_and_load_subscription_data(subscription_create_update_schema)
    if error_body:
        return jsonify(error_body), status_code

    session = db_session() # Get session for this request
    try:
        new_subscription = Subscription(
            id=uuid.uuid4(),
            target_url=data['target_url'], # type: ignore[reportGeneralTypeIssues]
            secret=data.get('secret'), # type: ignore[reportOptionalIterable]
            event_type_filter=data.get('event_type_filter') # type: ignore[reportOptionalIterable]
        )

        session.add(new_subscription)
        session.commit()
        cache_key = f"subscription:{new_subscription.id}"
        redis_client.setex(cache_key, Config.CACHE_EXPIRY_SECONDS, json.dumps({
             'target_url': new_subscription.target_url,
             'secret': new_subscription.secret,
             'event_type_filter': new_subscription.event_type_filter
        }))


        return jsonify(subscription_schema.dump(new_subscription)), 201
    except IntegrityError:
        session.rollback()
        print(f"Integrity error creating subscription (e.g., duplicate ID if not using UUID default correctly)")
        return jsonify({"message": "Integrity error creating subscription"}), 400
    except Exception as e:
        session.rollback()
        print(f"Error creating subscription: {e}")
        return jsonify({"message": "An error occurred"}), 500
    finally:
        db_session.remove() # Ensure session is closed


@api_bp.route('/subscriptions', methods=['GET'])
def list_subscriptions():
    """Lists all webhook subscriptions."""
    session = db_session()
    try:
        subscriptions = session.query(Subscription).all()
        return jsonify(subscriptions_schema.dump(subscriptions)), 200
    except Exception as e:
        print(f"Error listing subscriptions: {e}")
        return jsonify({"message": "An error occurred"}), 500
    finally:
        db_session.remove() # Ensure session is closed

@api_bp.route('/subscriptions/<uuid:sub_id>', methods=['GET'])
def get_subscription(sub_id):
    """Gets details for a specific subscription."""
    session = db_session()
    try:
        subscription = session.query(Subscription).filter_by(id=sub_id).first()
        if not subscription:
            return jsonify({"message": "Subscription not found"}), 404

        return jsonify(subscription_schema.dump(subscription)), 200
    except Exception as e:
        print(f"Error getting subscription {sub_id}: {e}")
        return jsonify({"message": "An error occurred"}), 500
    finally:
        db_session.remove() # Ensure session is closed

@api_bp.route('/subscriptions/<uuid:sub_id>', methods=['PUT']) # type: ignore[reportReturnType]
def update_subscription(sub_id):
    """Updates a specific subscription."""
    data, error_body, status_code = get_and_load_subscription_data(subscription_create_update_schema, partial=True)

    if error_body:
        return jsonify(error_body), status_code

    session = db_session() # Get session for this request
    try:
        subscription = session.query(Subscription).filter_by(id=sub_id).first()
        if not subscription:
            return jsonify({"message": "Subscription not found"}), 404

        for key, value in data.items(): # type: ignore[reportOptionalIterable]
            setattr(subscription, key, value)

        session.commit()
        cache_key = f"subscription:{subscription.id}"
        redis_client.setex(cache_key, Config.CACHE_EXPIRY_SECONDS, json.dumps({
            'target_url': subscription.target_url,
            'secret': subscription.secret,
            'event_type_filter': subscription.event_type_filter
        }))

        return jsonify(subscription_schema.dump(subscription)), 200
    except IntegrityError:
        session.rollback()
        print(f"Integrity error updating subscription {sub_id}")
        return jsonify({"message": "Integrity error updating subscription"}), 400
    except Exception as e:
        session.rollback()
        print(f"Error updating subscription {sub_id}: {e}")
        return jsonify({"message": "An error occurred"}), 500
    finally:
        db_session.remove() # Ensure session is closed

@api_bp.route('/subscriptions/<uuid:sub_id>', methods=['DELETE'])
def delete_subscription(sub_id):
    """Deletes a specific subscription."""
    session = db_session()
    try:
        subscription = session.query(Subscription).filter_by(id=sub_id).first()
        if not subscription:
            return jsonify({"message": "Subscription not found"}), 404

        session.delete(subscription)
        session.commit()
        cache_key = f"subscription:{sub_id}"
        redis_client.delete(cache_key)

        return jsonify({"message": "Subscription deleted"}), 200
    except Exception as e:
        session.rollback()
        print(f"Error deleting subscription {sub_id}: {e}")
        return jsonify({"message": "An error occurred"}), 500
    finally:
        db_session.remove()
