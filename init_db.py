from app.database import engine, Base
Base.metadata.create_all(bind=engine)