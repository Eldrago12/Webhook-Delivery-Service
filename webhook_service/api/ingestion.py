from flask import request, jsonify, g
from . import api_bp
from ..database import db_session
from ..models import Subscription, DeliveryTask
from ..celery_app import celery_app
from ..cache import redis_client
from ..config import Config
import uuid
import json
import hmac
import hashlib
import time
from ..tasks import process_delivery

@api_bp.route('/ingest/<uuid:sub_id>', methods=['POST'])
def ingest_webhook(sub_id):
    """Ingests a webhook payload and queues it for delivery."""
    if not request.json:
        return jsonify({"message": "Request body must be JSON"}), 415

    payload = request.json
    session = None

    try:
        cache_key = f"subscription:{sub_id}"
        sub_details = redis_client.get(cache_key)
        subscription = None
        if sub_details:
            try:
                subscription = json.loads(sub_details) # type: ignore[reportGeneralTypeIssues]
                print(f"Webhook {sub_id}: Fetched subscription {sub_id} from cache.")
            except json.JSONDecodeError:
                print(f"Webhook {sub_id}: Cache decode error for {sub_id}, fetching from DB.")
                # Delete bad cache entry
                redis_client.delete(cache_key)
                sub_details = None

        if not subscription:
            db_subscription = db_session.query(Subscription).filter_by(id=sub_id).first()
            if not db_subscription:
                 db_session.remove()
                 return jsonify({"message": "Subscription not found"}), 404

            # Cache the subscription details from DB
            subscription = {
                'target_url': db_subscription.target_url,
                'secret': db_subscription.secret,
                'event_type_filter': db_subscription.event_type_filter
            }
            redis_client.setex(cache_key, Config.CACHE_EXPIRY_SECONDS, json.dumps(subscription))
            db_session.remove()
            print(f"Webhook {sub_id}: Fetched subscription {sub_id} from DB and cached.")


        # --- 2. Bonus: Signature Verification ---
        secret = subscription.get('secret')
        if secret: # type: ignore[reportGeneralTypeIssues] # <-- Added ignore
            signature_header = request.headers.get(Config.WEBHOOK_SECRET_HEADER)
            if not signature_header:
                print(f"Webhook {sub_id}: Signature header missing.")
                return jsonify({"message": "Signature header missing"}), 401

            try:
                hash_method, signature = signature_header.split('=', 1)
            except ValueError:
                 print(f"Webhook {sub_id}: Invalid signature header format.")
                 return jsonify({"message": "Invalid signature header format"}), 400

            if hash_method != 'sha256':
                 print(f"Webhook {sub_id}: Unsupported signature hash method: {hash_method}")
                 return jsonify({"message": "Unsupported signature hash method"}), 400
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                request.data,
                hashlib.sha256
            ).hexdigest()

            # Secure comparison to prevent timing attacks
            if not hmac.compare_digest(expected_signature, signature):
                 print(f"Webhook {sub_id}: Invalid signature.")
                 return jsonify({"message": "Invalid signature"}), 401

            print(f"Webhook {sub_id}: Signature verified successfully.")


        # --- 3. Bonus: Event Type Filtering ---
        event_type_filter = subscription.get('event_type_filter')
        event_type = request.headers.get(Config.WEBHOOK_EVENT_TYPE_HEADER)
        if event_type_filter and event_type: # type: ignore[reportGeneralTypeIssues] # <-- Added ignore
             if event_type_filter != event_type: # type: ignore[reportGeneralTypeIssues] # <-- Added ignore
                 print(f"Webhook {sub_id}: Event type '{event_type}' filtered by '{event_type_filter}'. Skipping delivery.")
                 # Log the filtered event if desired
                 return jsonify({"message": f"Event type '{event_type}' filtered, delivery skipped"}), 202 # Accepted, but not queued

             print(f"Webhook {sub_id}: Event type '{event_type}' matches filter '{event_type_filter}'. Proceeding to queue.")
        elif event_type_filter and not event_type: # type: ignore[reportGeneralTypeIssues] # <-- Added ignore
            print(f"Webhook {sub_id}: Event type filter '{event_type_filter}' exists, but no '{Config.WEBHOOK_EVENT_TYPE_HEADER}' header provided. Skipping delivery.")
            return jsonify({"message": f"Subscription has event type filter, but no '{Config.WEBHOOK_EVENT_TYPE_HEADER}' header provided. Delivery skipped"}), 202


        # --- 4. Create Delivery Task in DB ---
        # Get a new DB session specifically for creating the task
        # This session is needed to commit the new task before sending to queue
        session = db_session()

        new_task = DeliveryTask(
            id=uuid.uuid4(),
            subscription_id=sub_id,
            payload=payload,
            status='pending',
            attempts_count=0
        )

        session.add(new_task)
        session.commit()
        task_id = new_task.id

        print(f"Webhook {sub_id}: Delivery task {task_id} created.")


        # --- 5. Send Task to Celery Queue ---
        # Use delay() as a shortcut for apply_async() with args
        # Ignore Pyright's confusion about the .delay() method
        process_delivery.delay(str(task_id)) # type: ignore[reportGeneralTypeIssues] # <-- Added ignore


        print(f"Webhook {sub_id}: Task {task_id} queued.")

        # --- 6. Return 202 Accepted ---
        # Include the task ID in the response for status tracking
        return jsonify({"message": "Webhook received and queued", "task_id": task_id}), 202

    except Exception as e:
        if session and session.is_active:
             session.rollback()
        print(f"Error during webhook ingestion for subscription {sub_id}: {e}")
        return jsonify({"message": "An internal error occurred during ingestion"}), 500
    finally:
        if session:
             db_session.remove()
