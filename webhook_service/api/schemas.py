from marshmallow import Schema, fields, validate, ValidationError
import uuid

# Custom UUID field for Marshmallow
class UUIDField(fields.UUID):
     def _deserialize(self, value, attr, data, **kwargs):
         if value is None:
             return None
         if isinstance(value, uuid.UUID):
             return value
         if isinstance(value, str):
             try:
                 uuid.UUID(value)
                 return uuid.UUID(value)
             except ValueError:
                 raise ValidationError("Not a valid UUID string.")
         raise ValidationError("Expected a string or UUID.")

# Schema for Subscription creation/update input
class SubscriptionCreateUpdateSchema(Schema):
    target_url = fields.URL(required=True, validate=validate.Length(min=1, max=255))
    secret = fields.String(validate=validate.Length(max=255), allow_none=True, missing=None)
    event_type_filter = fields.String(validate=validate.Length(max=255), allow_none=True, missing=None) # Bonus

# Schema for Subscription output
class SubscriptionSchema(SubscriptionCreateUpdateSchema):
    id = UUIDField(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

# Schema for Delivery Attempt output
class DeliveryAttemptSchema(Schema):
    id = UUIDField(dump_only=True)
    delivery_task_id = UUIDField(dump_only=True)
    attempt_number = fields.Integer(dump_only=True)
    timestamp = fields.DateTime(dump_only=True)
    outcome = fields.String(dump_only=True)
    http_status = fields.Integer(dump_only=True, allow_none=True)
    error_details = fields.String(dump_only=True, allow_none=True)

# Schema for Delivery Task output (for status endpoint)
class DeliveryTaskSchema(Schema):
    id = UUIDField(dump_only=True)
    subscription_id = UUIDField(dump_only=True)
    payload = fields.Dict(dump_only=True)
    status = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    last_attempt_at = fields.DateTime(dump_only=True, allow_none=True)
    next_attempt_at = fields.DateTime(dump_only=True, allow_none=True)
    attempts_count = fields.Integer(dump_only=True)
    last_http_status = fields.Integer(dump_only=True, allow_none=True)
    last_error = fields.String(dump_only=True, allow_none=True)



# Instantiate schemas
subscription_create_update_schema = SubscriptionCreateUpdateSchema()
subscription_schema = SubscriptionSchema()
subscriptions_schema = SubscriptionSchema(many=True)

delivery_attempt_schema = DeliveryAttemptSchema()
delivery_attempts_schema = DeliveryAttemptSchema(many=True)

delivery_task_schema = DeliveryTaskSchema()
