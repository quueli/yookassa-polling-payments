import os
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

from config import settings

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), unique=True, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=func.now())


class DatabaseManager:
    def __init__(self, database_url: str = None):
        url = database_url or settings.database_url
        if url.startswith("sqlite:///"):
            os.makedirs(os.path.dirname(url[len("sqlite:///"):]) or ".", exist_ok=True)
        self.engine = create_engine(url)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)

    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)

    def create_order(self, user_id: int, amount: float) -> Order:
        with self.SessionLocal() as db:
            order = Order(
                order_id=f"ORD-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",
                user_id=user_id,
                amount=round(amount, 2),
            )
            db.add(order)
            db.commit()
            db.refresh(order)
            return order

    def get_order(self, order_id: str):
        with self.SessionLocal() as db:
            return db.query(Order).filter(Order.order_id == order_id).first()

    def update_order_status(self, order_id: str, status: str) -> bool:
        with self.SessionLocal() as db:
            order = db.query(Order).filter(Order.order_id == order_id).first()
            if not order:
                return False
            order.status = status
            db.commit()
            return True


db_manager = DatabaseManager()
