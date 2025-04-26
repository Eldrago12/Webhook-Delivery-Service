import requests
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .celery_app import celery_app
from .database import db_session
from .models import DeliveryTask, DeliveryAttempt, Subscription
from .config import Config
from .cache import redis_client


@celery_app.task(bind=True, max_retries=Config.MAX_RETRIES, default_retry_delay=Config.RETRY_BASE_DELAY_SECONDS)
def process_delivery(self, delivery_task_id_str):
    """
    Celery task to process and attempt delivery of a webhook.
    Handles retries using Celery's built-in mechanism.
    """
    session = db_session()
    delivery_task_id = uuid.UUID(delivery_task_id_str)
    task = None

    try:
        task = session.query(DeliveryTask).filter_by(id=delivery_task_id).first()
        if not task:
            print(f"Task {delivery_task_id} not found in DB, skipping delivery.")
            # Ensure session is closed if task wasn't found and we exit early
            session.close()
            return # Task somehow disappeared, cannot proceed

        if task.status in ['pending', 'retrying']:
             task.status = 'processing' # type: ignore[reportAssignmentType]

        cache_key = f"subscription:{task.subscription_id}"
        sub_details = redis_client.get(cache_key)
        subscription = None

        if sub_details:
            try:
                subscription = json.loads(sub_details) # type: ignore[reportGeneralTypeIssues]
                print(f"Task {delivery_task_id}: Fetched subscription {task.subscription_id} from cache.")
            except json.JSONDecodeError:
                print(f"Task {delivery_task_id}: Cache decode error for {task.subscription_id}, fetching from DB.")
                redis_client.delete(cache_key)


        if not subscription: # If not found in cache or decode failed
            db_subscription = session.query(Subscription).filter_by(id=task.subscription_id).first()
            if not db_subscription:
                print(f"Task {delivery_task_id}: Subscription {task.subscription_id} not found in DB. Marking task failed.")
                task.status = 'failed' # type: ignore[reportAssignmentType]
                task.last_attempt_at = datetime.now(timezone.utc) # type: ignore[reportAssignmentType]
                task.last_error = "Subscription not found during delivery." # type: ignore[reportAssignmentType]
                final_attempt = DeliveryAttempt(
                    id=uuid.uuid4(),
                    delivery_task_id=task.id,
                    attempt_number=task.attempts_count + 1,
                    timestamp=task.last_attempt_at,
                    outcome='permanently_failed',
                    error_details=task.last_error
                )
                session.add(final_attempt)
                session.commit()
                session.close()
                return

            # Cache the subscription details from DB
            subscription = {
                'target_url': db_subscription.target_url,
                'secret': db_subscription.secret,
                'event_type_filter': db_subscription.event_type_filter
            }
            redis_client.setex(cache_key, Config.CACHE_EXPIRY_SECONDS, json.dumps(subscription))
            print(f"Task {delivery_task_id}: Fetched subscription {task.subscription_id} from DB and cached.")


        target_url = subscription.get('target_url')
        if not target_url: # type: ignore[reportGeneralTypeIssues]
             print(f"Task {delivery_task_id}: Subscription {task.subscription_id} has no target_url. Marking task failed.")
             task.status = 'failed' # type: ignore[reportAssignmentType]
             task.last_attempt_at = datetime.now(timezone.utc) # type: ignore[reportAssignmentType]
             task.last_error = "Subscription target_url is missing." # type: ignore[reportAssignmentType]
             final_attempt = DeliveryAttempt(
                 id=uuid.uuid4(),
                 delivery_task_id=task.id,
                 attempt_number=task.attempts_count + 1,
                 timestamp=task.last_attempt_at,
                 outcome='permanently_failed',
                 error_details=task.last_error
             )
             session.add(final_attempt)
             session.commit()
             session.close()
             return

        attempt_outcome = 'failed_attempt'
        http_status = None
        error_details = None

        print(f"Task {delivery_task_id}: Attempt {task.attempts_count + 1} delivering to {target_url}")

        try:
            response = requests.post(
                target_url, # type: ignore[reportGeneralTypeIssues]
                json=task.payload,
                timeout=Config.DELIVERY_TIMEOUT_SECONDS
            )
            http_status = response.status_code

            if 200 <= http_status < 300:
                attempt_outcome = 'success'
                print(f"Task {delivery_task_id}: Delivery successful (Status: {http_status})")
            else:
                error_details = f"Non-2xx status code: {http_status}. Response: {response.text[:200]}"
                print(f"Task {delivery_task_id}: Delivery failed (Status: {http_status})")

        except requests.exceptions.Timeout:
            error_details = f"Delivery timeout after {Config.DELIVERY_TIMEOUT_SECONDS} seconds."
            print(f"Task {delivery_task_id}: Delivery timed out.")
        except requests.exceptions.ConnectionError as e:
             error_details = f"Connection error: {e}"
             print(f"Task {delivery_task_id}: Connection error.")
        except requests.exceptions.RequestException as e:
            error_details = f"Request error: {e}"
            print(f"Task {delivery_task_id}: Request error.")
        except Exception as e:
             error_details = f"Unexpected error during delivery HTTP request: {e}"
             print(f"Task {delivery_task_id}: Unexpected HTTP request error.")

        task.attempts_count += 1 # type: ignore[reportAssignmentType]
        task.last_attempt_at = datetime.now(timezone.utc) # type: ignore[reportAssignmentType]
        task.last_http_status = http_status # type: ignore[reportAssignmentType]
        task.last_error = error_details # type: ignore[reportAssignmentType]

        new_attempt = DeliveryAttempt(
            id=uuid.uuid4(),
            delivery_task_id=task.id,
            attempt_number=task.attempts_count,
            timestamp=task.last_attempt_at,
            outcome=attempt_outcome,
            http_status=http_status,
            error_details=error_details
        )
        session.add(new_attempt)


        if attempt_outcome == 'success':
            task.status = 'succeeded' # type: ignore[reportAssignmentType]
            task.next_attempt_at = None # type: ignore[reportAssignmentType]
            print(f"Task {delivery_task_id}: Marked as succeeded.")
            session.commit()
            session.close()

        elif task.attempts_count >= self.max_retries:
            task.status = 'failed' # type: ignore[reportAssignmentType]
            task.next_attempt_at = None # type: ignore[reportAssignmentType]
            new_attempt.outcome = 'permanently_failed' # Update the outcome for the log # type: ignore[reportAssignmentType]
            print(f"Task {delivery_task_id}: Max retries ({self.max_retries}) reached. Marked as failed.")
            session.commit()
            session.close()

        else:
            # It's a failed attempt and retries are left
            task.status = 'retrying' # type: ignore[reportAssignmentType]
            # Calculate the delay for the *next* attempt
            delay_seconds = Config.RETRY_BASE_DELAY_SECONDS * (Config.RETRY_FACTOR ** (task.attempts_count - 1)) # For attempt_count = 1, (1-1)=0, factor^0 = 1, delay = base # type: ignore[reportAssignmentType]
            delay_seconds = min(delay_seconds, Config.MAX_RETRY_DELAY_SECONDS)
            task.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds) # type: ignore[reportAssignmentType]

            print(f"Task {delivery_task_id}: Failed. Retrying attempt {task.attempts_count} in {delay_seconds} seconds.")
            session.commit()
            session.close()
            raise self.retry(exc=Exception(error_details), countdown=delay_seconds)


    except Exception as e:
        print(f"FATAL Error processing task {delivery_task_id}: {e}")
        if session and session.is_active:
             session.rollback()
             session.close()
        log_session = None
        try:
            delivery_task_id_for_log = task.id if task else delivery_task_id
            attempt_number_for_log = task.attempts_count + 1 if task else 1


            fatal_attempt = DeliveryAttempt(
                 id=uuid.uuid4(),
                 delivery_task_id=delivery_task_id_for_log,
                 attempt_number=attempt_number_for_log,
                 timestamp=datetime.now(timezone.utc),
                 outcome='permanently_failed',
                 error_details=f"Fatal internal error processing task {delivery_task_id}: {e}"
             )

            log_session = db_session()
            log_session.add(fatal_attempt)

            if task:
                 task.status = 'failed' # type: ignore[reportAssignmentType]
                 task.last_attempt_at = datetime.now(timezone.utc) # type: ignore[reportAssignmentType]
                 task.last_error = fatal_attempt.error_details # type: ignore[reportAssignmentType]
                 task.next_attempt_at = None # type: ignore[reportAssignmentType]
                 log_session.merge(task)

            log_session.commit()
            print(f"Logged fatal error for task {delivery_task_id}.")
        except Exception as log_e:
             print(f"CRITICAL: Failed to log fatal error for task {delivery_task_id}: {log_e}")
        finally:
             if 'log_session' in locals() and log_session:
                 log_session.close()
        raise # Re-raise the original exception

    finally:
        if session and session.is_active:
             session.close()
