import json
import logging
from pathlib import Path
from datetime import datetime
from database import engine, SessionLocal
from models import Base, Trade

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    # 1. Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")

    # 2. Find JSON files
    trades_dir = Path(__file__).parent.parent / 'data' / 'trades'
    if not trades_dir.exists():
        logger.info("No trades directory found. Skipping data migration.")
        return

    json_files = list(trades_dir.glob('*.json'))
    logger.info(f"Found {len(json_files)} trade files.")

    db = SessionLocal()
    count = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Check if already exists
            if db.query(Trade).filter(Trade.id == data.get('id')).first():
                continue

            # Parse fields
            date_str = data.get('date') or data.get('created_at')
            
            # Helper for safe float conversion
            def safe_float(val):
                if val is None or val == '': return None
                try: return float(val)
                except: return None

            # Map JSON fields to Model fields
            trade = Trade(
                id=data.get('id'),
                created_at=datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else datetime.utcnow(),
                date=date_str,
                action=data.get('action'),
                ticker=data.get('ticker'),
                ticker_symbol=data.get('ticker_symbol'),
                market=data.get('market'),
                price=safe_float(data.get('entry_price')) or safe_float(data.get('price')),
                quantity=safe_float(data.get('quantity')),
                amount=safe_float(data.get('total_value')) or safe_float(data.get('amount')),
                currency=data.get('currency', 'TWD'),
                category=data.get('category', 'STOCK'),
                asset_name=data.get('asset_name'),
                reason=data.get('reason'),
                status=data.get('status', 'HOLDING'),
                score=int(data.get('score')) if data.get('score') else None,
                rating=data.get('rating'),
                suggestion=data.get('suggestion'),
                rsi=safe_float(data.get('rsi')),
                trend=data.get('trend'),
                ma5=safe_float(data.get('ma5')),
                ma20=safe_float(data.get('ma20')),
                macd=safe_float(data.get('macd')),
                stop_loss=safe_float(data.get('stop_loss')),
                target_1=safe_float(data.get('target_1')),
                target_2=safe_float(data.get('target_2')),
            )
            
            db.add(trade)
            count += 1
            
        except Exception as e:
            logger.error(f"Failed to migrate {json_file}: {e}")

    db.commit()
    logger.info(f"Successfully migrated {count} trades.")
    db.close()

if __name__ == "__main__":
    migrate()
