# Webhook-Delivery-Service

This project implements a robust, scalable, and reliable webhook delivery service. It provides API endpoints for managing webhook subscriptions, ingesting incoming webhook events, and asynchronously delivering them to target URLs with a retry mechanism. The service is containerized using Docker and orchestrated with Docker Compose for local development and deployment.





<img width="1680" alt="Screenshot 2025-04-27 at 2 13 53 PM" src="https://github.com/user-attachments/assets/1db53bce-8bc1-4bf5-af85-5efa26316617" />







TRY IT OUT HERE!! 🚀


***[Webhook-Delivery-Service Live](https://d2zpp4v3snrpit.cloudfront.net)***

You can also try out the Backend-Server via curl or Postman!! 🚀

***[Backend-Server URL](https://d2zpp4v3snrpit.cloudfront.net/api)***

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Core Requirements Implemented](#core-requirements-implemented)
- [Technical Requirements Met](#technical-requirements-met)
- [Bonus Points Achieved](#bonus-points-achieved)
- [Database Schema and Indexing](#database-schema-and-indexing)
- [Local Setup and Running with Docker Compose](#local-setup-and-running-with-docker-compose)
    - [Prerequisites](#prerequisites)
    - [Cloning the Repository](#cloning-the-repository)
    - [Environment Variables](#environment-variables)
    - [Building and Running Services](#building-and-running-services)
    - [Running Database Migrations](#running-database-migrations)
    - [Accessing Services](#accessing-services)
- [API Documentation and Examples](#api-documentation-and-examples)
    - [Base URL](#base-url)
    - [Authentication](#authentication)
    - [Subscriptions API (`/api/subscriptions`)](#subscriptions-api-apiv1subscriptions)
        - [Create Subscription (`POST`)](#create-subscription-post)
        - [List Subscriptions (`GET`)](#list-subscriptions-get)
        - [Get Subscription by ID (`GET`)](#get-subscription-by-id-get)
        - [Update Subscription by ID (`PUT`)](#update-subscription-by-id-put)
        - [Delete Subscription by ID (`DELETE`)](#delete-subscription-by-id-delete)
    - [Ingestion API (`/api/ingest/{sub_id}`)](#ingestion-api-apiv1ingestsub_id)
    - [Status API (`/api/status/delivery_tasks/{task_id}`)](#status-api-apiv1statusdelivery_taskstask_id)
- [Deployment](#deployment)
    - [Live Application Link](#live-application-link)
    - [Deployment Strategy](#deployment-strategy)
    - [Cost Estimation (Free Tier)](#cost-estimation-free-tier)
        - [Assumptions](#assumptions)
        - [Estimated Monthly Cost](#estimated-monthly-cost)
- [Performance and Scalability Considerations](#performance-and-scalability-considerations)

## Project Overview

This project provides a backend service for managing and delivering webhooks. Key features include:

* **Subscription Management:** API endpoints to create, list, retrieve, update, and delete webhook subscriptions.

* **Asynchronous Ingestion:** An endpoint to receive webhook payloads, quickly acknowledge them, and queue them for background processing.

* **Reliable Delivery:** Background workers attempt to deliver payloads to target URLs.

* **Retry Mechanism:** Automatic retries with exponential backoff for failed deliveries.

* **Logging and Status:** Detailed logging of delivery attempts and an API to check the status of individual deliveries.

* **Caching:** Uses Redis to cache subscription details for faster lookups during delivery.

* **Signature Verification:** Optionally verifies incoming webhook payloads using HMAC-SHA256.

* **Event Type Filtering:** Optionally filters webhook delivery based on event type.

## Architecture

The service follows a microservice-like architecture, leveraging several components orchestrated by Docker Compose:

* **Flask (`app` service):** A lightweight Python web framework used for the API endpoints (Subscription CRUD, Ingestion, Status).

* **PostgreSQL (`db` service):** A relational database used to store subscription details, delivery tasks, and delivery attempts.

* **RabbitMQ (`rabbitmq` service):** A message broker used by Celery to queue delivery tasks.

* **Redis (`redis` service):** An in-memory data structure store used as a cache for subscription details and as the result backend for Celery.

* **Celery Worker (`worker` service):** A background worker process that consumes tasks from the RabbitMQ queue and handles the actual webhook delivery attempts.

* **Celery Beat (`beat` service):** A scheduler that periodically runs maintenance tasks, such as cleaning up old delivery logs.

* **Alembic Migrator (`migrator` service):** A tool for database schema migrations.





The workflow is as follows:

1.  An external system sends a webhook payload to the `/api/ingest/{sub_id}` endpoint.

2.  The Flask `app` service receives the request, performs optional signature verification and event type filtering, creates a `DeliveryTask` record in the PostgreSQL database, and immediately queues the task for asynchronous processing using Celery/RabbitMQ. It then returns a `202 Accepted` response.

3.  A Celery worker consumes the task from the queue.

4.  The worker retrieves the subscription details (preferably from the Redis cache, falling back to the database).

5.  The worker attempts to send the webhook payload to the target URL via HTTP `POST`.

6.  Based on the HTTP response or network errors, the worker logs the delivery attempt and updates the `DeliveryTask` status in the database.

7.  If the delivery fails and the maximum retry count has not been reached, the worker schedules the task for a future retry using Celery's retry mechanism with exponential backoff.

8.  The Celery beat service periodically runs a task to clean up `DeliveryAttempt` records older than the `LOG_RETENTION_HOURS` configuration.

## Core Requirements Implemented

The service successfully implements all core requirements:

* **Subscription Management:** Full CRUD operations are available via the `/api/subscriptions` endpoints. Subscriptions have a unique ID, target URL, and optional secret key and event type filter.

* **Webhook Ingestion:** The `/api/ingest/{sub_id}` endpoint accepts `POST` requests, creates a `DeliveryTask`, and queues it asynchronously, returning a `202 Accepted` response.

* **Asynchronous Delivery Processing:** The Celery worker processes queued tasks, retrieves subscription details, and attempts HTTP `POST` delivery with a configurable timeout.

* **Retry Mechanism:** Failed deliveries are automatically retried using Celery's built-in retry logic with configurable exponential backoff parameters (`RETRY_BASE_DELAY_SECONDS`, `RETRY_FACTOR`, `MAX_RETRY_DELAY_SECONDS`) and a maximum number of attempts (`MAX_RETRIES`).

* **Delivery Logging:** Each delivery attempt is logged in the `delivery_attempts` table, recording relevant details including outcome, status code, and error information.

* **Log Retention:** A Celery Beat task is configured to periodically clean up `DeliveryAttempt` records older than the `LOG_RETENTION_HOURS` configuration.

* **Status/Analytics Endpoint:** The `/api/v1/status/delivery_tasks/{task_id}` endpoint allows retrieving the status and history for a specific delivery task. (Note: An endpoint to list recent attempts for a subscription was not explicitly implemented but could be added).
* **Caching:** Redis is used to cache `Subscription` objects after the first lookup, reducing database load for subsequent delivery attempts to the same subscription.

## Technical Requirements Met

* **Language:** Python.

* **Framework:** Flask for the web API.

* **Database:** PostgreSQL, chosen for its reliability, ACID compliance, and suitability for structured data like subscriptions and logs, even with a potentially high volume of delivery attempts.

* **Asynchronous Tasks / Queueing:** Celery with RabbitMQ as the broker and Redis as the result backend provides a robust and scalable system for handling background tasks and retries.

* **Caching:** Redis is used to cache `Subscription` objects after the first lookup, reducing database load for subsequent delivery attempts to the same subscription.

* **Containerisation:** The entire application stack is containerized using Docker and orchestrated with `docker-compose.yml`. The local setup works with just Docker installed. Development and testing were performed on a Mac device.

* **Deployment:** The application is deployed to AWS Free Tier, with the backend running on an EC2 instance using Docker Compose and the frontend hosted on S3.

## Bonus Points Achieved

* **Payload Signature Verification:** The ingestion endpoint (`/api/ingest/{sub_id}`) implements signature verification. If a subscription has a secret configured, the incoming request is expected to have a signature header (`X-Webhook-Secret` by default) containing an HMAC-SHA256 hash of the raw payload body, signed with the subscription's secret. Requests with missing or invalid signatures for subscriptions requiring a secret are rejected with a `401 Unauthorized` response.


* **Event Type Filtering:** Subscriptions can optionally specify an `event_type_filter`. The ingestion endpoint expects the incoming event type in a header (`X-Webhook-Event` by default). If a subscription has a filter and the incoming event type does not match, the webhook is accepted (`202`) but the delivery task is skipped, and a corresponding message is returned in the response.

## Database Schema and Indexing

The database schema consists of three main tables:

* `subscriptions`: Stores details about each webhook subscription.

    * `id` (UUID, Primary Key): Unique identifier for the subscription.

    * `target_url` (String): The URL where webhooks are sent.

    * `secret` (String, Nullable): Optional secret key for signature verification.

    * `event_type_filter` (String, Nullable): Optional filter for specific event types.

    * `created_at` (DateTime): Timestamp when the subscription was created.

    * `updated_at` (DateTime): Timestamp when the subscription was last updated.

* `delivery_tasks`: Represents an instance of an incoming webhook payload that needs to be delivered.

    * `id` (UUID, Primary Key): Unique identifier for the delivery task.

    * `subscription_id` (UUID, Foreign Key to `subscriptions.id`): Links the task to a specific subscription.

    * `payload` (JSONB): The original JSON payload of the webhook.

    * `status` (String): Current status of the task (e.g., 'pending', 'retrying', 'succeeded', 'failed').

    * `attempts_count` (Integer): Number of delivery attempts made so far.

    * `created_at` (DateTime): Timestamp when the task was created.

    * `last_attempt_at` (DateTime, Nullable): Timestamp of the last delivery attempt.

    * `next_attempt_at` (DateTime, Nullable): Timestamp scheduled for the next retry attempt.

    * `last_http_status` (Integer, Nullable): HTTP status code of the last attempt.

    * `last_error` (String, Nullable): Details of the last error encountered.

* `delivery_attempts`: Logs each individual attempt to deliver a `DeliveryTask`.

    * `id` (UUID, Primary Key): Unique identifier for the attempt log.

    * `delivery_task_id` (UUID, Foreign Key to `delivery_tasks.id`): Links the attempt to a task.

    * `attempt_number` (Integer): The sequential number of this attempt for the task.

    * `outcome` (String): Result of the attempt ('success', 'failed_attempt', 'permanently_failed').

    * `http_status` (Integer, Nullable): HTTP status code received.

    * `error_details` (String, Nullable): Specific error message.

    * `timestamp` (DateTime): Timestamp of the attempt.

**Indexing Strategy:**

* `subscriptions`:

    * Index on `id` (Primary Key is automatically indexed).
    * Consider an index on `event_type_filter` if filtering is heavily used.

* `delivery_tasks`:
    * Index on `id` (Primary Key).
    * Index on `subscription_id` (Foreign Key is typically indexed, but confirm). This is crucial for retrieving tasks for a specific subscription.
    * Index on `status`: Useful for querying tasks in specific states (e.g., 'pending', 'retrying').
    * Index on `next_attempt_at`: Critical for the Celery worker to efficiently find tasks that are ready for retry.

* `delivery_attempts`:
    * Index on `id` (Primary Key).
    * Index on `delivery_task_id` (Foreign Key): Essential for retrieving all attempts for a specific task.
    * Index on `timestamp`: Necessary for the log retention cleanup task to efficiently find old records.

## Local Setup and Running with Docker Compose

These instructions assume you have Docker and Docker Compose installed on your machine (tested on macOS).

### Prerequisites

* Docker (includes Docker Engine and Docker Compose)

### Cloning the Repository

```bash
git clone https://github.com/Eldrago12/Webhook-Delivery-Service.git
cd Webhook-Delivery-Service
```

### Environment Variables

Create a `.env` file in the root of the project directory. This file will hold configuration values for the services.

```bash
cp .env .env
```

Edit the `.env` file and fill in the necessary values. At a minimum, you'll need:

```Ini, TOML
# Database
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=webhook_db
DATABASE_URL=postgresql://<span class="math-inline">\{POSTGRES\_USER\}\:</span>{POSTGRES_PASSWORD}@db:5432/<span class="math-inline">\{POSTGRES\_DB\}
\# RabbitMQ \(Celery Broker\)
RABBITMQ\_DEFAULT\_USER\=guest
RABBITMQ\_DEFAULT\_PASS\=guest
CELERY\_BROKER\_URL\=amqp\://</span>{RABBITMQ_DEFAULT_USER}:<span class="math-inline">\{RABBITMQ\_DEFAULT\_PASS\}@rabbitmq\:5672//
\# Redis \(Celery Result Backend & Cache\)
REDIS\_HOST\=redis
REDIS\_PORT\=6379
REDIS\_CACHE\_URL\=redis\://</span>{REDIS_HOST}:${REDIS_PORT}/0
CACHE_EXPIRY_SECONDS=3600 # Cache subscription details for 1 hour

# Application Settings
SECRET_KEY=your-very-secret-key-change-this # Flask secret key
DELIVERY_TIMEOUT_SECONDS=10 # Timeout for webhook HTTP requests
WEBHOOK_SECRET_HEADER=X-Hub-Signature-256 # Header name for signature verification
WEBHOOK_EVENT_TYPE_HEADER=X-Event-Type # Header name for event type filtering

# Celery Retry Strategy
MAX_RETRIES=5 # Maximum number of delivery attempts
RETRY_BASE_DELAY_SECONDS=10 # Initial delay before first retry (seconds)
RETRY_FACTOR=3 # Factor to multiply delay by for subsequent retries
MAX_RETRY_DELAY_SECONDS=900 # Maximum delay between retries (15 minutes)

# Log Retention
LOG_RETENTION_HOURS=72 # Keep delivery attempt logs for 72 hours
```

### Building and Running Services

Build the Docker images and start the services defined in `docker-compose.yml`:

```bash
docker-compose build
docker-compose up -d
```

This will:

- Build your custom application image (used by `app`, `worker`, `beat`, `migrator`).
- Pull public images for `db`, `rabbitmq`, and `redis`.
- Start all services in detached mode (`-d`).

### Running Database Migrations

After the `db` service is healthy, run database migrations using the `migrator` service. This sets up the necessary tables.

```bash
docker-compose run --rm migrator alembic upgrade head
```

- `run`: Executes a one-off command in a service container.

- `--rm`: Removes the container after the command finishes.

- `migrator`: The name of the service defined in docker-compose.yml for migrations.

- `alembic upgrade head`: The Alembic command to apply all pending migrations.

### Accessing Services

- **Flask API**: Accessible at http://localhost:8000 (port 8000 is mapped to the app container's port 5000).

- **RabbitMQ Management UI**: Accessible at http://localhost:15672 (login with guest/guest or your configured credentials).

- **Redis**: Accessible internally by other containers on port 6379.

To stop the services:

```bash
docker-compose down
```

To stop and remove volumes (useful for a clean start, but will lose DB/MQ/Redis data):

```bash
docker-compose down -v
```

## API Documentation and Examples

The API is served by the `app` service.

### Base URL

- **Local**: `http://localhost:8000`

- **Deployed**: `https://d2zpp4v3snrpit.cloudfront.net/api`

### Authentication

API endpoints for Subscription management (`/api/subscriptions`) do not require authentication in this implementation.

The Ingestion endpoint (`/api/ingest/{sub_id}`) requires signature verification if the target subscription has a secret configured. The expected signature is an `HMAC-SHA256 hash` of the raw request body, signed with the subscription's secret. The signature should be provided in the `X-Hub-Signature-256` header (configurable via `WEBHOOK_SECRET_HEADER`), prefixed with `sha256=`.

### Subscriptions API (/api/subscriptions)

**Create Subscription** `(POST)`

Creates a new webhook subscription.

**Request:**

```bash
curl -X POST http://localhost:8000/api/subscriptions \
-H "Content-Type: application/json" \
-d '{
  "target_url": "https://webhook.site/your-unique-id",
  "secret": "my-secure-secret-for-signing",
  "event_type_filter": "order.created"
}'
```

- `target_url` (string, required): The URL to send webhooks to.

- `secret` (string, optional): A secret key for signature verification.

- `event_type_filter` (string, optional): Only deliver webhooks with this event type.

**Response (201 Created):**

```bash
{
  "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "target_url": "https://webhook.site/your-unique-id",
  "secret": "my-secure-secret-for-signing",
  "event_type_filter": "order.created",
  "created_at": "2023-10-27T10:00:00.123456+00:00",
  "updated_at": "2023-10-27T10:00:00.123456+00:00"
}
```

**List Subscriptions** `(GET)`

Retrieves a list of all subscriptions.

**Request:**

```bash
curl http://localhost:8000/api/subscriptions
```

**Response (200 OK):**

```bash
[
  {
    "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "target_url": "https://webhook.site/your-unique-id",
    "secret": "my-secure-secret-for-signing",
    "event_type_filter": "order.created",
    "created_at": "2023-10-27T10:00:00.123456+00:00",
    "updated_at": "2023-10-27T10:00:00.123456+00:00"
  },
  {
    "id": "b2c3d4e5-f6a7-8901-2345-67890abcdef1",
    "target_url": "http://another-service.com/webhook",
    "secret": null,
    "event_type_filter": null,
    "created_at": "2023-10-27T10:05:00.123456+00:00",
    "updated_at": "2023-10-27T10:05:00.123456+00:00"
  }
]
```

**Get Subscription by ID** `(GET)`

Retrieves details for a specific subscription.

**Request:**

```bash
curl http://localhost:8000/api/subscriptions/a1b2c3d4-e5f6-7890-1234-567890abcdef
```

**Response (200 OK):**

```bash
{
  "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "target_url": "https://webhook.site/your-unique-id",
  "secret": "my-secure-secret-for-signing",
  "event_type_filter": "order.created",
  "created_at": "2023-10-27T10:00:00.123456+00:00",
  "updated_at": "2023-10-27T10:00:00.123456+00:00"
}
```

**Response (404 Not Found):**

```bash
{
  "error": "Subscription not found"
}
```

**Update Subscription by ID** `(PUT)`

Updates details for a specific subscription. Provide only the fields you want to change.

**Request:**

```bash
curl -X PUT http://localhost:8000/api/subscriptions/a1b2c3d4-e5f6-7890-1234-567890abcdef \
-H "Content-Type: application/json" \
-d '{
  "target_url": "https://new-webhook.site/updated-id",
  "event_type_filter": "product.updated"
}'
```

**Response (200 OK):**

```bash
{
  "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "target_url": "https://new-webhook.site/updated-id",
  "secret": "my-secure-secret-for-signing", # Secret remains unchanged if not provided in update
  "event_type_filter": "product.updated",
  "created_at": "2023-10-27T10:00:00.123456+00:00",
  "updated_at": "2023-10-27T10:15:00.123456+00:00" # Updated timestamp
}
```

**Response (404 Not Found):**

```bash
{
  "error": "Subscription not found"
}
```

**Delete Subscription by ID** `(DELETE)`

Deletes a specific subscription

**Request:**

```bash
curl -X DELETE http://localhost:8000/api/subscriptions/a1b2c3d4-e5f6-7890-1234-567890abcdef
```

**Response (200 OK):**

```bash
{
  "message": "Subscription deleted"
}
```

**Response (404 Not Found):**

```bash
{
  "error": "Subscription not found"
}
```

**Ingestion API** `(/api/ingest/{sub_id})`

Accepts incoming webhook payloads and queues them for delivery

**Request:**

```bash
# Example with signature verification (if subscription has a secret)
# You would need to calculate the signature client-side based on the raw payload body and the subscription secret.
# Example using Python (replace secret and payload):
# import hmac, hashlib, json
# secret = b'my-secure-secret-for-signing'
# payload = {"event": "order.created", "data": {"order_id": 123}}
# payload_bytes = json.dumps(payload).encode('utf-8')
# signature = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
# signature_header = f'sha256={signature}'

curl -X POST http://localhost:8000/api/v1/ingest/a1b2c3d4-e5f6-7890-1234-567890abcdef \
-H "Content-Type: application/json" \
-H "X-Event-Type: order.created" \
-H "X-Hub-Signature-256: sha256=calculated_signature_here" \
-d '{
  "event": "order.created",
  "data": {
    "order_id": 12345,
    "amount": 100.0,
    "customer": "demo@example.com"
  },
  "timestamp": "2025-04-26T21:47:17.140015+00:00"
}'
```

- `{sub_id}` (path parameter, UUID): The ID of the target subscription.

- `Content-Type: application/json` (header, required): Indicates the body is JSON.

- `X-Event-Type` (header, string, configurable via `WEBHOOK_EVENT_TYPE_HEADER`): The type of the event. Used for filtering.

- `X-Hub-Signature-256` (header, string, configurable via `WEBHOOK_SECRET_HEADER`, optional): The payload signature. Required if the subscription has a secret. Format: `sha256=<hex_signature>`.

- Request Body (JSON, required): The webhook payload to be delivered.

**Response (202 Accepted):**

```bash
{
  "message": "Webhook received and queued",
  "task_id": "f9e0d1c2-b3a4-5678-9012-34567890abcd"
}
```

**Response (202 Accepted - Filtered):**

```bash
{
  "message": "Event type 'order.created' filtered, delivery skipped"
}
```

**Response (401 Unauthorized - Invalid Signature):**

```bash
{
  "message": "Invalid signature"
}
```

**Response (401 Unauthorized - Signature Header Missing):**

```bash
{
  "message": "Signature header missing"
}
```

**Response (404 Not Found - Subscription ID):**

```bash
{
  "message": "Subscription not found"
}
```

**Response (415 Unsupported Media Type - Invalid JSON):**

```bash
{
  "message": "Request body must be JSON"
}
```

**Status API** (/api/status/delivery_tasks/{task_id})

Retrieves the status and history for a specific delivery task

**Request:**

```bash
curl http://localhost:8000/api/status/delivery_tasks/f9e0d1c2-b3a4-5678-9012-34567890abcd
```

- `{task_id}` (path parameter, UUID): The ID of the delivery task.

**Response (200 OK):**

```bash
{
  "task_id": "f9e0d1c2-b3a4-5678-9012-34567890abcd",
  "subscription_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "status": "succeeded",
  "attempts_count": 1,
  "created_at": "2025-04-27T05:00:00.123456+00:00",
  "last_attempt_at": "2025-04-27T05:00:01.123456+00:00",
  "next_attempt_at": null,
  "last_http_status": 200,
  "last_error": null,
  "attempts": [
    {
      "attempt_number": 1,
      "outcome": "success",
      "http_status": 200,
      "error_details": null,
      "timestamp": "2025-04-27T05:00:01.123456+00:00"
    }
    # More attempts if retries occurred
  ]
}
```

**Response (404 Not Found):**

```bash
{
  "message": "Delivery task not found"
}
```

## Deployment

The application is deployed to AWS Free Tier.

### Live Application Link

The frontend UI is hosted via Cloudfront and AWS S3 and can be accessed here:

https://d2zpp4v3snrpit.cloudfront.net/

The backend API is running on an EC2 instance and is accessible via its public cloudfront DNS Proxy `https://d2zpp4v3snrpit.cloudfront.net/api` as over the top of EC2 where the backend is deployed there is `Cloudfront Proxy` to enable `https` without `SSL and Domain name` and bypass browser checking for `sha256`.


### Deployment Strategy

The backend services (Flask app, Celery worker/beat, PostgreSQL, RabbitMQ, Redis) are deployed together on a single AWS EC2 instance using Docker Compose. The frontend (the minimal UI HTML file) is hosted separately on Cloudfront via S3.


This "all-in-one" deployment on EC2 using Docker Compose simplifies the setup for demonstration purposes and fits within the free tier limits for moderate traffic. However, for production environments, it is generally recommended to use managed AWS services for stateful components (RDS for PostgreSQL, Amazon MQ for RabbitMQ, ElastiCache for Redis) and deploy the stateless application components (Flask app, Celery worker/beat) to a container orchestration service like ECS Fargate for better scalability, availability, and operational management but it would incur charges.

### Cost Estimation (Free Tier):

This estimation assumes continuous operation `(24x7)` and moderate traffic (5000 webhooks ingested/day, average 1.2 delivery attempts per webhook).

**Assumptions**

* Using AWS Free Tier eligible services.
* Backend runs on a single `t2.small` EC2 instance (which costs `$0.023/hr` which is `$15.45/month`).
* Uses standard SSD (gp2 or gp3) EBS volume for EC2 (free tier includes 30GB).
* Frontend hosted on S3 (free tier includes 5GB standard storage, 20,000 Get Requests, 2,000 Put Requests).
* No significant data transfer costs beyond free tier limits.
* No additional AWS services like Load Balancers, NAT Gateways which would incur costs.
* Database, RabbitMQ, and Redis are running as containers on the EC2 instance; their resource usage is part of the EC2 cost.
* Moderate traffic level does not exceed the capacity of the `t2.small` instance or free tier request limits for S3.

**Estimated Monthly Cost**

* **EC2 (t2.small):** $15.45
* **EBS (for EC2):** $0 (within free tier limits)
* **S3 (Frontend Hosting):** $0 (within free tier limits for storage and requests for a simple static site)
* **Data Transfer:** $0 (within free tier limits)

**Total Estimated Monthly Cost:** Approximately $15.45.


## Performance and Scalability Considerations

- **Caching (Redis)**: Caching subscription details in Redis significantly improves performance during webhook ingestion and delivery task processing by reducing the number of database reads. This is crucial for handling a high volume of incoming webhooks efficiently.

- **Asynchronous Processing (Celery/RabbitMQ)**: Decoupling ingestion from delivery using a message queue prevents the ingestion endpoint from being blocked by slow or failing webhook deliveries. This allows the service to quickly acknowledge incoming webhooks, improving perceived performance and resilience. Celery workers can be scaled independently to handle increased delivery load.

- **Database Indexing**: Appropriate indexing on `subscription_id`, `status`, `next_attempt_at`, and `timestamp` in the PostgreSQL database is essential for efficient querying by the API (status checks) and the Celery worker (finding tasks to process/retry, cleaning up logs).


## Contribute & Connect

If you find any improvements or have better approaches, feel free to contribute! 🚀

Let's connect and discuss further optimization of this project:

- **LinkedIn**: [Sirshak Dolai](https://www.linkedin.com/in/sirshak-dolai)

⭐️ **If you find this repo helpful, consider giving it a star!** ⭐️
