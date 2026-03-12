"""
NoFOMO - 投資組合與交易管理模組
"""

import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Any, Optional

from utils import safe_json_read, safe_json_write
from market_data import get_stock_price

logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).parent.parent / 'data'
TRADES_DIR = DATA_DIR / 'trades'
PORTFOLIO_FILE = DATA_DIR / 'portfolio.json'

DATA_DIR.mkdir(parents=True, exist_ok=True)
TRADES_DIR.mkdir(parents=True, exist_ok=True)


def get_all_trades() -> List[Dict]:
    """讀取所有交易記錄"""
    trades = []
    # 使用 glob 讀取所有 .json 檔案
    for f in TRADES_DIR.glob('*.json'):
        try:
            trade_data = safe_json_read(f)
            if trade_data:
                trades.append(trade_data)
        except Exception as e:
            logger.error(f'Failed to read trade file {f}: {e}')
    
    # 依日期排序（新到舊）
    trades.sort(key=lambda x: x.get('date', '') or x.get('created_at', ''), reverse=True)
    return trades


def add_trade(trade_data: Dict) -> str:
    """新增交易記錄"""
    # 生成唯一 ID (含微秒避免衝突)
    trade_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    trade_data['id'] = trade_id
    if 'created_at' not in trade_data:
        trade_data['created_at'] = datetime.now().isoformat()
    
    filepath = TRADES_DIR / f"{trade_id}.json"
    safe_json_write(filepath, trade_data)
    
    logger.info(f'New trade added: {trade_data.get("ticker")} {trade_data.get("action")} {trade_data.get("quantity")}')
    return trade_id


def _detect_ticker_symbol(display_ticker: str, stored_symbol: str = '') -> tuple:
    """
    從 ticker 判斷市場別與完整 yfinance symbol。
    回傳: (ticker_symbol, market)
    """
    # 若已有儲存的 symbol (例如從前端傳來的 BTC-USD)
    if stored_symbol:
        if stored_symbol.endswith('-USD'):
            return stored_symbol, 'CRYPTO'
        if stored_symbol.endswith('.TW'):
            return stored_symbol, 'TW'
        return stored_symbol, 'US'
    
    # 簡單判斷規則
    if display_ticker.isdigit():
        return display_ticker + '.TW', 'TW'
    if display_ticker in ['BTC', 'ETH', 'USDT', 'SOL', 'BNB', 'XRP', 'DOGE']:
        return f"{display_ticker}-USD", 'CRYPTO'
        
    return display_ticker, 'US'


def aggregate_positions(trades: List[Dict]) -> Dict[str, Dict]:
    """
    將交易清單聚合成目前持倉（含平均成本、市場別）
    回傳格式:
      { 'AAPL': { 'quantity': 10, 'cost': 1500.0, 'avg_price': 150.0,
                  'ticker_symbol': 'AAPL', 'market': 'US' }, ... }
    """
    positions: Dict[str, Dict] = {}

    sorted_trades = sorted(trades, key=lambda x: x.get('date', '') or x.get('created_at', ''))

    for trade in sorted_trades:
        ticker = trade.get('ticker', '').upper()
        action = trade.get('action', '').lower()
        quantity = int(trade.get('quantity', 0))
        price = float(trade.get('entry_price', 0) or trade.get('price', 0))

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
    回傳: (details_list, total_market_value)
    """
    def fetch_one(ticker, pos):
        # 使用完整 yfinance symbol 查詢（含 .TW）
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
            'market': pos.get('market', 'US'),   # 'US' | 'TW'
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

    # 使用 ThreadPoolExecutor 並行查詢
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
    # 預設 TWD/USD 為 0
    balances = {'TWD': 0.0, 'USD': 0.0} 
    
    sorted_trades = sorted(trades, key=lambda x: x.get('date', '') or x.get('created_at', ''))
    
    for trade in sorted_trades:
        action = trade.get('action', '').upper()
        
        # 判斷幣別 (優先使用明確指定的 currency)
        currency = trade.get('currency')
        if not currency:
            # 相容舊有股票交易
            market = trade.get('market', 'US')
            currency = 'USD' if market == 'US' else 'TWD'
            
        # 取得金額 (股票交易用 total_value，現金/資產用 amount)
        amount = float(trade.get('total_value', 0) or trade.get('amount', 0))
        
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

    # 1. 股票持倉
    positions = aggregate_positions(trades)
    total_cost = sum(p['cost'] for p in positions.values())
    
    # 2. 股票現價
    position_details, stock_value = enrich_positions_with_prices(positions)

    # 3. 現金餘額 (多幣別)
    cash_balances = calculate_cash_balances(trades)
    
    # 4. 其他資產
    other_assets = aggregate_other_assets(trades)
    
    # 5. 損益 (僅股票)
    total_pnl = stock_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    return {
        'cash_balances': cash_balances,
        'stock_value': round(stock_value, 2),
        'other_assets': other_assets,
        # total_assets 在後端難以精確加總(因多幣別)，交由前端換算
        'total_assets': 0, 
        'total_cost': round(total_cost, 2),
        'total_pnl': round(total_pnl, 2),
        'total_pnl_pct': round(total_pnl_pct, 2),
        'positions': position_details,
        'updated_at': datetime.now().isoformat()
    }


def get_trade_statistics() -> Dict:
    """交易統計分析"""
    trades = get_all_trades()
    if not trades:
        return {'message': 'No trades'}

    buy_trades = [t for t in trades if t.get('action', '').lower() == 'buy']
    sell_trades = [t for t in trades if t.get('action', '').lower() == 'sell']

    ticker_stats: Dict[str, Dict] = {}
    for trade in trades:
        ticker = trade.get('ticker', '').upper()
        if ticker not in ticker_stats:
            ticker_stats[ticker] = {'buy': 0, 'sell': 0, 'total': 0}
        action = trade.get('action', '').lower()
        if action in ticker_stats[ticker]:
            ticker_stats[ticker][action] += 1
        ticker_stats[ticker]['total'] += 1

    recent = trades[:5]
    
    return {
        'total_trades': len(trades),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades),
        'by_ticker': ticker_stats,
        'recent_trades': recent,
        'timestamp': datetime.now().isoformat()
    }


def get_risk_assessment() -> Dict:
    """風險評估"""
    summary = get_portfolio_summary()
    positions = summary.get('positions', [])
    total_value = summary.get('total_assets', 0) # 修正: 用總資產還是證券價值? api.py 原本用 total_value (stock_value + cash?) no, api.py used total_value from enrich which is STOCK value.
    # Check original api.py: 
    # total_value = perf_data['total_value'] -> this was stock value.
    # But denominator: max_position = max(p['value'] / total_value ...)
    # If total_value is 0 (all cash), div by zero.
    
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
