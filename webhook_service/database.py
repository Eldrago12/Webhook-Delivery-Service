from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from .config import Config

# Database engine
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    """Creates database tables based on models."""
    import webhook_service.models
    Base.metadata.create_all(bind=engine)

def shutdown_session(exception=None):
    """Removes the session, typically called at the end of a request or task."""
    db_session.remove()
