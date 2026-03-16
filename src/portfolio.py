"""
NoFOMO - 投資組合與交易管理模組 (Database Version)
"""

import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Any, Optional

from database import SessionLocal
from models import Trade, PortfolioSnapshot
from market_data import get_stock_price

logger = logging.getLogger(__name__)

def to_dict(trade: Trade) -> Dict:
    """Convert SQLAlchemy model to dict for compatibility"""
    return {
        'id': trade.id,
        'created_at': trade.created_at.isoformat() if trade.created_at else None,
        'date': trade.date,
        'action': trade.action,
        'ticker': trade.ticker,
        'ticker_symbol': trade.ticker_symbol,
        'market': trade.market,
        'entry_price': trade.price, # Map back to entry_price for compatibility
        'price': trade.price,
        'quantity': trade.quantity,
        'total_value': trade.amount, # Map back to total_value
        'amount': trade.amount,
        'currency': trade.currency,
        'category': trade.category,
        'asset_name': trade.asset_name,
        'reason': trade.reason,
        'status': trade.status,
        'score': trade.score,
        'rating': trade.rating,
        'suggestion': trade.suggestion,
        'rsi': trade.rsi,
        'trend': trade.trend,
        'ma5': trade.ma5,
        'ma20': trade.ma20,
        'macd': trade.macd,
        'stop_loss': trade.stop_loss,
        'target_1': trade.target_1,
        'target_2': trade.target_2,
        # NoFOMO review fields
        'motivation': trade.motivation,
        'emotion': trade.emotion,
        'lesson': trade.lesson,
        'next_action': trade.next_action,
        'reviewed_at': trade.reviewed_at.isoformat() if trade.reviewed_at else None,
    }

def get_all_trades() -> List[Dict]:
    """讀取所有交易記錄 (From DB)"""
    db = SessionLocal()
    try:
        # 依 created_at 倒序排列 (新到舊)
        trades = db.query(Trade).order_by(Trade.created_at.desc()).all()
        return [to_dict(t) for t in trades]
    finally:
        db.close()

def review_trade(trade_id: str, review_data: Dict) -> bool:
    """儲存交易復盤資料"""
    db = SessionLocal()
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            return False
        trade.motivation = review_data.get('motivation', trade.motivation)
        trade.emotion = review_data.get('emotion', trade.emotion)
        trade.lesson = review_data.get('lesson', trade.lesson)
        trade.next_action = review_data.get('next_action', trade.next_action)
        trade.reviewed_at = datetime.now()
        db.commit()
        logger.info(f"Trade reviewed: {trade_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to review trade: {e}")
        return False
    finally:
        db.close()

def delete_trade(trade_id: str) -> bool:
    """刪除交易記錄"""
    db = SessionLocal()
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if trade:
            db.delete(trade)
            db.commit()
            logger.info(f"Trade deleted: {trade_id}")
            # Update snapshot after deletion
            create_snapshot()
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete trade: {e}")
        return False
    finally:
        db.close()

def add_trade(trade_data: Dict) -> str:
    """新增交易記錄 (To DB)"""
    db = SessionLocal()
    try:
        # 生成唯一 ID
        trade_id = trade_data.get('id') or datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        created_at = datetime.now()
        
        # Helper for safe float conversion
        def safe_float(val):
            if val is None or val == '': return None
            try: return float(val)
            except: return None

        trade = Trade(
            id=trade_id,
            created_at=created_at,
            date=trade_data.get('date', created_at.isoformat()),
            action=trade_data.get('action'),
            ticker=trade_data.get('ticker'),
            ticker_symbol=trade_data.get('ticker_symbol'),
            market=trade_data.get('market'),
            price=safe_float(trade_data.get('entry_price') or trade_data.get('price')),
            quantity=safe_float(trade_data.get('quantity')),
            amount=safe_float(trade_data.get('total_value') or trade_data.get('amount')),
            currency=trade_data.get('currency', 'TWD'),
            category=trade_data.get('category', 'STOCK'),
            asset_name=trade_data.get('asset_name'),
            reason=trade_data.get('reason'),
            status=trade_data.get('status', 'HOLDING'),
            score=int(trade_data.get('score')) if trade_data.get('score') else None,
            rating=trade_data.get('rating'),
            suggestion=trade_data.get('suggestion'),
            rsi=safe_float(trade_data.get('rsi')),
            trend=trade_data.get('trend'),
            ma5=safe_float(trade_data.get('ma5')),
            ma20=safe_float(trade_data.get('ma20')),
            macd=safe_float(trade_data.get('macd')),
            stop_loss=safe_float(trade_data.get('stop_loss')),
            target_1=safe_float(trade_data.get('target_1')),
            target_2=safe_float(trade_data.get('target_2')),
        )
        
        db.add(trade)
        db.commit()
        logger.info(f'New trade added to DB: {trade_id}')
        
        # Update snapshot after adding
        create_snapshot()
        
        return trade_id
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add trade: {e}")
        raise e
    finally:
        db.close()

def edit_trade(trade_id: str, updates: Dict) -> bool:
    """編輯交易記錄"""
    db = SessionLocal()
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            return False
            
        def safe_float(val):
            if val is None or val == '': return None
            try: return float(val)
            except: return None

        # 可編輯的欄位
        if 'date' in updates: trade.date = updates['date']
        if 'ticker' in updates: trade.ticker = updates['ticker']
        if 'price' in updates: 
            trade.price = safe_float(updates['price'])
        if 'quantity' in updates: 
            trade.quantity = safe_float(updates['quantity'])
        if 'amount' in updates:
            trade.amount = safe_float(updates['amount'])
        
        # 自動重新計算總金額 (如果修改了價或量)
        if trade.price is not None and trade.quantity is not None:
            trade.amount = trade.price * trade.quantity

        db.commit()
        logger.info(f"Trade edited: {trade_id}")
        
        create_snapshot()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to edit trade: {e}")
        return False
    finally:
        db.close()

def _detect_ticker_symbol(display_ticker: str, stored_symbol: str = '') -> tuple:
    """
    從 ticker 判斷市場別與完整 yfinance symbol。
    回傳: (ticker_symbol, market)
    """
    if stored_symbol:
        if stored_symbol.endswith('-USD'):
            return stored_symbol, 'CRYPTO'
        if stored_symbol.endswith('.TW'):
            return stored_symbol, 'TW'
        return stored_symbol, 'US'
    
    if display_ticker.isdigit():
        return display_ticker + '.TW', 'TW'
    if display_ticker in ['BTC', 'ETH', 'USDT', 'SOL', 'BNB', 'XRP', 'DOGE']:
        return f"{display_ticker}-USD", 'CRYPTO'
        
    return display_ticker, 'US'


def aggregate_positions(trades: List[Dict]) -> Dict[str, Dict]:
    """
    將交易清單聚合成目前持倉（含平均成本、市場別）
    """
    positions: Dict[str, Dict] = {}

    # 需按時間正序計算成本 (舊到新)
    sorted_trades = sorted(trades, key=lambda x: x.get('date', '') or x.get('created_at', ''))

    for trade in sorted_trades:
        category = trade.get('category', 'STOCK')
        if category != 'STOCK' and category != 'CRYPTO': # Skip cash/assets
             pass

        action = trade.get('action', '').lower()
        if action not in ['buy', 'sell']:
            continue

        ticker = trade.get('ticker', '').upper()
        quantity = trade.get('quantity', 0) or 0
        price = float(trade.get('entry_price', 0) or trade.get('price', 0) or 0)

        if not ticker:
            continue

        if ticker not in positions:
            sym, mkt = _detect_ticker_symbol(
                ticker,
                trade.get('ticker_symbol', '')
            )
            positions[ticker] = {
                'quantity': 0, 'cost': 0.0, 'avg_price': 0.0,
                'ticker_symbol': sym, 'market': mkt
            }

        if action == 'buy':
            old_qty  = positions[ticker]['quantity']
            old_cost = positions[ticker]['cost']
            new_cost = old_cost + (quantity * price)
            new_qty  = old_qty + quantity
            positions[ticker]['quantity']  = new_qty
            positions[ticker]['cost']      = new_cost
            positions[ticker]['avg_price'] = new_cost / new_qty if new_qty > 0 else 0.0

        elif action == 'sell':
            current_avg = positions[ticker]['avg_price']
            sell_qty = min(quantity, positions[ticker]['quantity'])
            positions[ticker]['quantity'] -= sell_qty
            positions[ticker]['cost']     -= sell_qty * current_avg

    return {t: p for t, p in positions.items() if p['quantity'] > 0}


def enrich_positions_with_prices(positions: Dict[str, Dict]) -> Tuple[List[Dict], float]:
    """
    並行查詢現價，計算每個部位的損益
    """
    def fetch_one(ticker, pos):
        symbol = pos.get('ticker_symbol', ticker)
        price_data = get_stock_price(symbol)
        current_price = 0.0

        if 'error' not in price_data:
            current_price = price_data.get('current_price', 0.0)

        if current_price == 0:
            current_price = pos['avg_price']

        current_value = pos['quantity'] * current_price
        cost = pos['cost']
        pnl = current_value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0.0

        return {
            'ticker': ticker,
            'ticker_symbol': symbol,
            'market': pos.get('market', 'US'),
            'quantity': pos['quantity'],
            'avg_price': round(pos['avg_price'], 2),
            'current_price': round(current_price, 2),
            'value': round(current_value, 2),
            'cost': round(cost, 2),
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
        }

    details = []
    total_value = 0.0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            ticker: executor.submit(fetch_one, ticker, pos)
            for ticker, pos in positions.items()
        }
        for ticker, future in futures.items():
            try:
                result = future.result()
                if result:
                    details.append(result)
                    total_value += result['value']
            except Exception as e:
                logger.error(f"Error enriching position for {ticker}: {e}")

    return details, total_value


def calculate_cash_balances(trades: List[Dict]) -> Dict[str, float]:
    """從交易紀錄計算各幣別現金餘額"""
    balances = {'TWD': 0.0, 'USD': 0.0} 
    
    sorted_trades = sorted(trades, key=lambda x: x.get('date', '') or x.get('created_at', ''))
    
    for trade in sorted_trades:
        action = trade.get('action', '').upper()
        
        currency = trade.get('currency')
        if not currency:
            market = trade.get('market', 'US')
            currency = 'USD' if market == 'US' else 'TWD'
            
        amount = float(trade.get('total_value', 0) or trade.get('amount', 0) or 0)
        
        if currency not in balances:
            balances[currency] = 0.0
            
        if action == 'DEPOSIT':
            balances[currency] += amount
        elif action == 'WITHDRAW':
            balances[currency] -= amount
        elif action == 'BUY':
            balances[currency] -= amount
        elif action == 'SELL':
            balances[currency] += amount
            
    return {k: round(v, 2) for k, v in balances.items()}


def aggregate_other_assets(trades: List[Dict]) -> List[Dict]:
    """聚合其他資產（房產、奢侈品等）的最新估值"""
    assets_map = {}
    
    sorted_trades = sorted(trades, key=lambda x: x.get('date', '') or x.get('created_at', ''))
    
    for trade in sorted_trades:
        if trade.get('category') == 'ASSET':
            name = trade.get('asset_name')
            if not name: continue
            
            # 取最後一次更新的值
            assets_map[name] = {
                'name': name,
                'value': float(trade.get('amount', 0)),
                'currency': trade.get('currency', 'TWD'),
                'updated_at': trade.get('date') or trade.get('created_at')
            }
            
    return list(assets_map.values())


def get_portfolio_summary() -> Dict:
    """取得完整的投資組合摘要"""
    trades = get_all_trades()
    
    if not trades:
        return {
            'cash_balances': {'TWD': 0, 'USD': 0},
            'stock_value': 0,
            'other_assets': [],
            'total_assets': 0,
            'total_cost': 0,
            'total_pnl': 0,
            'total_pnl_pct': 0,
            'positions': []
        }

    positions = aggregate_positions(trades)
    total_cost = sum(p['cost'] for p in positions.values())
    
    position_details, stock_value = enrich_positions_with_prices(positions)

    cash_balances = calculate_cash_balances(trades)
    
    other_assets = aggregate_other_assets(trades)
    
    total_pnl = stock_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    return {
        'cash_balances': cash_balances,
        'stock_value': round(stock_value, 2),
        'other_assets': other_assets,
        'total_assets': 0, 
        'total_cost': round(total_cost, 2),
        'total_pnl': round(total_pnl, 2),
        'total_pnl_pct': round(total_pnl_pct, 2),
        'positions': position_details,
        'updated_at': datetime.now().isoformat()
    }

def create_snapshot():
    """建立資產快照"""
    try:
        summary = get_portfolio_summary()
        
        # 簡單匯率換算 (USD -> TWD)
        # 這裡為了快照一致性，假設 1 USD = 32 TWD，或者應該從 API 抓
        # 為了避免循環依賴或網絡延遲，這裡用固定值或簡單估算
        # 理想情況是傳入匯率，但這裡簡化處理
        usd_rate = 32.0 

        stock_val = 0.0
        crypto_val = 0.0
        
        # 分離 Stock / Crypto
        for p in summary['positions']:
            val_twd = p['value']
            if p.get('market') != 'TW':
                val_twd = p['value'] * usd_rate # 假設非 TW 都是 USD 計價
            
            if p.get('market') == 'CRYPTO':
                crypto_val += val_twd
            else:
                stock_val += val_twd

        cash_val = summary['cash_balances'].get('TWD', 0) + (summary['cash_balances'].get('USD', 0) * usd_rate)
        
        other_val = sum(a['value'] for a in summary['other_assets']) # 假設其他資產都是 TWD
        
        total_equity = stock_val + crypto_val + cash_val + other_val
        
        db = SessionLocal()
        snapshot = PortfolioSnapshot(
            total_equity=total_equity,
            stock_value=stock_val,
            crypto_value=crypto_val,
            cash_value=cash_val,
            other_assets_value=other_val,
            pnl=summary['total_pnl'],
            pnl_percent=summary['total_pnl_pct']
        )
        db.add(snapshot)
        db.commit()
        db.close()
        logger.info(f"Portfolio snapshot created: {total_equity}")
    except Exception as e:
        logger.error(f"Failed to create snapshot: {e}")

def get_portfolio_history(limit: int = 30) -> List[Dict]:
    """取得資產歷史紀錄"""
    db = SessionLocal()
    try:
        snapshots = db.query(PortfolioSnapshot).order_by(PortfolioSnapshot.date.asc()).all()
        # 簡單過濾：每天只取最後一筆 (如果一天有多筆)
        # 或者直接回傳所有，前端處理
        return [{
            'date': s.date.isoformat(),
            'total_equity': s.total_equity,
            'stock_value': s.stock_value,
            'crypto_value': s.crypto_value,
            'cash_value': s.cash_value,
            'other_assets_value': s.other_assets_value
        } for s in snapshots]
    finally:
        db.close()

def get_trade_statistics() -> Dict:
    """交易統計分析"""
    trades = get_all_trades()
    if not trades:
        return {'message': 'No trades'}

    buy_trades = [t for t in trades if t.get('action', '').lower() == 'buy']
    sell_trades = [t for t in trades if t.get('action', '').lower() == 'sell']

    ticker_stats: Dict[str, Dict] = {}
    for trade in trades:
        ticker = trade.get('ticker', '')
        if not ticker: continue
        ticker = ticker.upper()
        
        if ticker not in ticker_stats:
            ticker_stats[ticker] = {'buy': 0, 'sell': 0, 'total': 0}
        action = trade.get('action', '').lower()
        if action in ticker_stats[ticker]:
            ticker_stats[ticker][action] += 1
        ticker_stats[ticker]['total'] += 1

    recent = trades[:5]

    # FOMO statistics (from reviewed BUY trades)
    reviewed_buys = [t for t in buy_trades if t.get('reviewed_at')]
    motivation_dist: Dict[str, int] = {}
    emotion_dist: Dict[str, int] = {}
    fomo_trades = []
    planned_trades = []
    for t in reviewed_buys:
        m = t.get('motivation') or '其他'
        e = t.get('emotion') or '冷靜'
        motivation_dist[m] = motivation_dist.get(m, 0) + 1
        emotion_dist[e] = emotion_dist.get(e, 0) + 1
        if e == '非常FOMO':
            fomo_trades.append(t)
        elif e == '冷靜':
            planned_trades.append(t)

    def avg_pnl(trade_list):
        vals = [t.get('amount') or 0 for t in trade_list if t.get('amount')]
        return round(sum(vals) / len(vals), 2) if vals else 0

    fomo_stats = {
        'reviewed_count': len(reviewed_buys),
        'fomo_count': len(fomo_trades),
        'fomo_rate': round(len(fomo_trades) / len(reviewed_buys) * 100, 1) if reviewed_buys else 0,
        'motivation_distribution': motivation_dist,
        'emotion_distribution': emotion_dist,
    }

    return {
        'total_trades': len(trades),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades),
        'by_ticker': ticker_stats,
        'recent_trades': recent,
        'fomo_stats': fomo_stats,
        'timestamp': datetime.now().isoformat()
    }


def get_risk_assessment() -> Dict:
    """風險評估"""
    summary = get_portfolio_summary()
    positions = summary.get('positions', [])
    stock_value = summary.get('stock_value', 0)
    
    if not positions or stock_value == 0:
        return {'risk_level': 'N/A', 'message': 'No positions'}

    # 集中度風險
    max_position_pct = max((p['value'] / stock_value) for p in positions)
    concentration_risk = 'HIGH' if max_position_pct > 0.4 else 'MEDIUM' if max_position_pct > 0.25 else 'LOW'

    # 勝率 (目前持倉獲利比率)
    profitable = sum(1 for p in positions if p['pnl'] > 0)
    win_rate = profitable / len(positions) * 100

    risk_score = 5
    if concentration_risk == 'HIGH':
        risk_score += 2
    elif concentration_risk == 'MEDIUM':
        risk_score += 1
    if win_rate < 40:
        risk_score += 2
    elif win_rate < 60:
        risk_score += 1

    risk_level = 'HIGH' if risk_score >= 7 else 'MEDIUM' if risk_score >= 4 else 'LOW'

    recommendations = []
    if concentration_risk == 'HIGH':
        recommendations.append('建議分散投資，降低單一標的比重')
    if win_rate < 50:
        recommendations.append('建議檢視虧損部位，考慮停損')
    if len(positions) < 3:
        recommendations.append('建議增加投資標的數量分散風險')

    return {
        'risk_level': risk_level,
        'risk_score': risk_score,
        'concentration': concentration_risk,
        'win_rate': round(win_rate, 1),
        'positions_count': len(positions),
        'recommendations': recommendations,
        'timestamp': datetime.now().isoformat()
    }
