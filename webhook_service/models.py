import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, text, func, TEXT
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy import Index
from .database import Base, engine

def generate_uuid():
    return str(uuid.uuid4())

class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    target_url = Column(String(255), nullable=False)
    secret = Column(String(255))
    event_type_filter = Column(String(255), index=True) # <-- Added index=True
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), index=True)

    delivery_tasks = relationship("DeliveryTask", back_populates="subscription", cascade="all, delete-orphan")
    def __repr__(self):
        return f"<Subscription(id='{self.id}', target_url='{self.target_url}')>"


class DeliveryTask(Base):
    __tablename__ = 'delivery_tasks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False)
    payload = Column(JSONB, nullable=False)
    # Index on status is defined in __table_args__
    status = Column(String(50), nullable=False, default='pending')
    # Add index to created_at
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True) # <-- Added index=True
    last_attempt_at = Column(DateTime(timezone=True))
    next_attempt_at = Column(DateTime(timezone=True))
    attempts_count = Column(Integer, nullable=False, default=0)
    last_http_status = Column(Integer)
    last_error = Column(TEXT)

    # Define relationship to subscription and attempts
    subscription = relationship("Subscription", back_populates="delivery_tasks")
    delivery_attempts = relationship("DeliveryAttempt", back_populates="delivery_task", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_delivery_tasks_subscription_id', subscription_id),
        Index('idx_delivery_tasks_status', status),
        Index('idx_delivery_tasks_next_attempt_at', next_attempt_at, postgresql_where=(text("status = 'retrying'"))),
    )

    def __repr__(self):
        return f"<DeliveryTask(id='{self.id}', status='{self.status}', attempts={self.attempts_count})>"


class DeliveryAttempt(Base):
    __tablename__ = 'delivery_attempts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    # Index on FK is defined in __table_args__
    delivery_task_id = Column(UUID(as_uuid=True), ForeignKey('delivery_tasks.id', ondelete='CASCADE'), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    outcome = Column(String(50), nullable=False)
    http_status = Column(Integer)
    error_details = Column(TEXT)

    delivery_task = relationship("DeliveryTask", back_populates="delivery_attempts")

    __table_args__ = (
        Index('idx_delivery_attempts_delivery_task_id', delivery_task_id),
        Index('idx_delivery_attempts_timestamp', timestamp),
    )

    def __repr__(self):
        return f"<DeliveryAttempt(id='{self.id}', task_id='{self.delivery_task_id}', attempt={self.attempt_number}, outcome='{self.outcome}')>"
