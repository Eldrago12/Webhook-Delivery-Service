from flask import jsonify, request
from sqlalchemy import desc
from . import api_bp
from ..database import db_session
from ..models import DeliveryTask, DeliveryAttempt, Subscription
from .schemas import delivery_task_schema, delivery_attempts_schema
import uuid

def validate_uuid_param(uuid_str):
    try:
        return uuid.UUID(uuid_str)
    except ValueError:
        return None

@api_bp.route('/status/delivery_tasks/<uuid:task_id>', methods=['GET'])
def get_delivery_task_status(task_id):
    """Gets the status and attempts for a specific delivery task."""
    try:
        task = db_session.query(DeliveryTask).filter_by(id=task_id).first()
        if not task:
            return jsonify({"message": "Delivery task not found"}), 404

        attempts = db_session.query(DeliveryAttempt)\
                             .filter_by(delivery_task_id=task_id)\
                             .order_by(DeliveryAttempt.attempt_number)\
                             .all()

        task_data = delivery_task_schema.dump(task)
        attempts_data = delivery_attempts_schema.dump(attempts)

        response_data = task_data
        response_data['attempts'] = attempts_data # type: ignore[reportGeneralTypeIssues]

        return jsonify(response_data), 200

    except Exception as e:
        print(f"Error getting status for task {task_id}: {e}")
        return jsonify({"message": "An error occurred"}), 500
    finally:
        db_session.remove()


@api_bp.route('/status/subscriptions/<uuid:sub_id>/attempts', methods=['GET'])
def list_subscription_attempts(sub_id):
    """Lists recent delivery attempts for a specific subscription."""
    try:
        subscription = db_session.query(Subscription).filter_by(id=sub_id).first()
        if not subscription:
             return jsonify({"message": "Subscription not found"}), 404


        recent_attempts = db_session.query(DeliveryAttempt)\
                                    .join(DeliveryTask)\
                                    .filter(DeliveryTask.subscription_id == sub_id)\
                                    .order_by(desc(DeliveryAttempt.timestamp))\
                                    .limit(20)\
                                    .all()

        return jsonify(delivery_attempts_schema.dump(recent_attempts)), 200

    except Exception as e:
        print(f"Error listing attempts for subscription {sub_id}: {e}")
        return jsonify({"message": "An error occurred"}), 500
    finally:
        db_session.remove()
