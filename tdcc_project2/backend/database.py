from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker
import os

# 獲取當前檔案的絕對路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "tdcc.db")

# 使用絕對路徑以確保不同執行環境下的穩定性
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 120}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

class TDCCData(Base):
    __tablename__ = "tdcc_data"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True) # YYYYMMDD
    stock_id = Column(String, index=True)
    level = Column(Integer)
    people = Column(Integer)
    shares = Column(Float)
    percent = Column(Float)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
