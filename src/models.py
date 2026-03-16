from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Trade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    date = Column(String) 
    
    action = Column(String, index=True)
    
    # Stock/Crypto info
    ticker = Column(String, index=True, nullable=True)
    ticker_symbol = Column(String, nullable=True)
    market = Column(String, nullable=True)
    
    # Transaction details
    price = Column(Float, nullable=True) # entry_price or price
    quantity = Column(Float, nullable=True)
    amount = Column(Float, nullable=True) # Total value or cash amount
    currency = Column(String, default='TWD')
    
    # Asset info
    category = Column(String, default='STOCK') # STOCK, CASH, ASSET
    asset_name = Column(String, nullable=True)
    
    # Analysis & Plan
    reason = Column(Text, nullable=True)
    status = Column(String, default='HOLDING')
    score = Column(Integer, nullable=True)
    rating = Column(String, nullable=True)
    suggestion = Column(String, nullable=True)
    
    # Technicals
    rsi = Column(Float, nullable=True)
    trend = Column(String, nullable=True)
    ma5 = Column(Float, nullable=True)
    ma20 = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    
    # Trade Management
    stop_loss = Column(Float, nullable=True)
    target_1 = Column(Float, nullable=True)
    target_2 = Column(Float, nullable=True)

    # Post-trade Review (NoFOMO)
    motivation = Column(String, nullable=True)   # 計劃布局/突破追買/看別人買/聽消息/其他
    emotion = Column(String, nullable=True)      # 冷靜/有點急/非常FOMO
    lesson = Column(Text, nullable=True)         # 學到什麼
    next_action = Column(Text, nullable=True)    # 下次怎麼做
    reviewed_at = Column(DateTime, nullable=True)

class Settings(Base):
    __tablename__ = "settings"
    
    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=True)

class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    total_equity = Column(Float) # Total Net Worth in TWD
    stock_value = Column(Float)
    crypto_value = Column(Float)
    cash_value = Column(Float)
    other_assets_value = Column(Float)
    pnl = Column(Float)
    pnl_percent = Column(Float)
