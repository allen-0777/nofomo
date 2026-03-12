import sys
from pathlib import Path

# 確保 src/ 在 import 路徑中
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

# Modules
import utils
import market_data
import portfolio

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR = Path(__file__).parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Data Paths (for Watchlist/Alerts)
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent.parent / 'data'
WATCHLIST_FILE = DATA_DIR / 'watchlist.json'
ALERTS_FILE = DATA_DIR / 'alerts.json'

# ---------------------------------------------------------------------------
# Watchlist & Alerts Management
# ---------------------------------------------------------------------------
_DEFAULT_WATCHLIST = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'JPM', 'V', 'WMT']

def _load_watchlist():
    return utils.safe_json_read(WATCHLIST_FILE, list(_DEFAULT_WATCHLIST))

def _save_watchlist(watchlist):
    utils.safe_json_write(WATCHLIST_FILE, watchlist)

def _load_alerts():
    return utils.safe_json_read(ALERTS_FILE, {})

def _save_alerts(alerts):
    utils.safe_json_write(ALERTS_FILE, alerts)

_watchlist = _load_watchlist()
_price_alerts = _load_alerts()

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route('/api/health')
def health():
    stats = market_data.get_cache_stats()
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'cache_size': stats['size'],
        'watchlist_count': len(_watchlist)
    })

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    market_data.clear_cache()
    return jsonify({'success': True, 'message': 'Cache cleared'})

@app.route('/api/quote')
def quote():
    ticker = request.args.get('ticker', '').upper()
    if not ticker:
        return jsonify({'error': 'Missing ticker'}), 400
    
    result = market_data.get_stock_price(ticker)
    if 'error' in result:
        return jsonify(result), 502
    return jsonify(result)

@app.route('/api/analyze')
def analyze():
    ticker = request.args.get('ticker', '').upper()
    if not ticker:
        return jsonify({'error': 'Missing ticker'}), 400

    analysis = market_data.technical_analysis(ticker)
    if 'error' in analysis:
        return jsonify(analysis), 502

    # 補充建議資訊 (可在前端做，但保持 API 相容性先留在後端)
    # analyzer.py 其實已經有 generate_suggestion，但這裡原本是手寫的
    # 我們沿用 analyzer 的 generate_suggestion 嗎？
    # 原本 api.py 是自己算的，為了保持相容，我們簡單補上
    price = analysis.get('current_price', 0)
    score = analysis.get('score', 3)
    suggestion_map = {5: '強烈買入', 4: '偏多買入', 3: '觀察等待', 2: '謹慎操作', 1: '不建議'}
    
    analysis['stop_loss'] = round(price * 0.95, 2)
    analysis['target_1'] = round(price * 1.10, 2)
    analysis['target_2'] = round(price * 1.20, 2)
    analysis['suggestion'] = suggestion_map.get(score, '觀察等待')
    analysis['rating'] = '⭐' * score
    
    return jsonify(analysis)

@app.route('/api/trades', methods=['GET'])
def get_trades():
    trades = portfolio.get_all_trades()
    return jsonify(trades)

@app.route('/api/trades', methods=['POST'])
def add_trade():
    data = request.json
    if not data:
        return jsonify({'error': 'Missing request body'}), 400

    required = ['ticker', 'action', 'quantity', 'entry_price']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing fields: {missing}'}), 400

    trade_id = portfolio.add_trade(data)
    return jsonify({'success': True, 'id': trade_id})

@app.route('/api/portfolio/summary')
def portfolio_summary():
    summary = portfolio.get_portfolio_summary()
    return jsonify(summary)

@app.route('/api/portfolio')
def get_portfolio():
    # 為了兼容性，導向 summary 或回傳精簡版
    # 原本是讀取 portfolio.json，現在我們統一用即時計算
    summary = portfolio.get_portfolio_summary()
    return jsonify(summary)

@app.route('/api/portfolio/performance')
def portfolio_performance():
    # 與 summary 類似，但格式可能略有不同
    summary = portfolio.get_portfolio_summary()
    return jsonify({
        'positions': summary['positions'],
        'total_value': summary['stock_value'],
        'total_cost': summary['total_cost'],
        'pnl': summary['total_pnl'],
        'pnl_percent': summary['total_pnl_pct'],
        'timestamp': summary['updated_at']
    })

@app.route('/api/batch-quote')
def batch_quote():
    tickers = request.args.get('tickers', '').upper().split(',')
    tickers = [t.strip() for t in tickers if t.strip()]

    if not tickers:
        return jsonify({'error': 'Missing tickers'}), 400
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {t: executor.submit(market_data.get_stock_price, t) for t in tickers}
        results = {t: f.result() for t, f in futures.items()}

    return jsonify(results)

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    return jsonify({'watchlist': _watchlist})

@app.route('/api/watchlist', methods=['POST'])
def update_watchlist():
    global _watchlist
    data = request.json
    if not data or 'watchlist' not in data:
        return jsonify({'error': 'Invalid request'}), 400
    
    _watchlist = [t.upper().strip() for t in data['watchlist'] if t.strip()]
    _save_watchlist(_watchlist)
    return jsonify({'success': True, 'watchlist': _watchlist})

@app.route('/api/history')
def get_history():
    ticker = request.args.get('ticker', '').upper()
    period = request.args.get('period', '1mo')
    
    if not ticker:
        return jsonify({'error': 'Missing ticker'}), 400

    try:
        hist = market_data.get_stock_history(ticker, period)
        if hist.empty:
            return jsonify({'error': 'No data'}), 404

        data = [
            {
                'date': idx.isoformat(),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume'])
            }
            for idx, row in hist.iterrows()
        ]
        return jsonify({
            'ticker': ticker,
            'period': period,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f'History error: {ticker} {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    return jsonify({'alerts': _price_alerts})

@app.route('/api/alerts', methods=['POST'])
def set_alert():
    data = request.json
    ticker = data.get('ticker', '').upper()
    try:
        target_price = float(data.get('target_price', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid target_price'}), 400
    
    condition = data.get('condition', 'above')

    if not ticker or target_price <= 0:
        return jsonify({'error': 'Invalid ticker or price'}), 400

    if ticker not in _price_alerts:
        _price_alerts[ticker] = []

    alert = {
        'target_price': target_price,
        'condition': condition,
        'created_at': datetime.now().isoformat(),
        'triggered': False
    }
    _price_alerts[ticker].append(alert)
    _save_alerts(_price_alerts)
    return jsonify({'success': True, 'alert': alert})

@app.route('/api/alerts/check')
def check_alerts():
    triggered = []
    any_changed = False

    for ticker, alerts in _price_alerts.items():
        current = market_data.get_stock_price(ticker)
        if 'error' in current:
            continue

        price = current['current_price']
        for alert in alerts:
            if alert['triggered']:
                continue

            is_triggered = (
                (alert['condition'] == 'above' and price >= alert['target_price']) or
                (alert['condition'] == 'below' and price <= alert['target_price'])
            )
            if is_triggered:
                alert['triggered'] = True
                alert['triggered_at'] = datetime.now().isoformat()
                alert['current_price'] = price
                triggered.append({
                    'ticker': ticker,
                    'target_price': alert['target_price'],
                    'condition': alert['condition'],
                    'current_price': price
                })
                any_changed = True

    if any_changed:
        _save_alerts(_price_alerts)

    return jsonify({'triggered': triggered, 'timestamp': datetime.now().isoformat()})

@app.route('/api/exchange-rate')
def exchange_rate():
    """取得多國貨幣對 TWD 即時匯率"""
    try:
        import yfinance as yf
        # 定義需要查詢的匯率對
        pairs = {
            'USD': 'USDTWD=X',
            'JPY': 'JPYTWD=X',
            'HKD': 'HKDTWD=X',
            'KRW': 'KRWTWD=X',
            'CNY': 'CNYTWD=X',
            'VND': 'VNDTWD=X'
        }
        
        # 批量查詢以提升效能
        tickers = " ".join(pairs.values())
        data = yf.download(tickers, period="1d", progress=False)['Close']
        
        rates = {'TWD': 1.0} # 基準幣別
        
        # 處理資料 (yfinance 回傳格式可能因單一/多個 ticker 而異)
        if len(pairs) == 1:
            # 只有一個時 data 是 Series
            rates['USD'] = round(float(data.iloc[-1]), 2)
        else:
            # 多個時 data 是 DataFrame
            # 取得最新一筆非空值
            latest = data.iloc[-1]
            for currency, ticker in pairs.items():
                val = latest.get(ticker)
                if val and val > 0:
                    rates[currency] = float(val)
                else:
                    # Fallback values if API fails specific pair
                    defaults = {'USD': 32.0, 'JPY': 0.21, 'HKD': 4.1, 'KRW': 0.024, 'CNY': 4.4, 'VND': 0.0013}
                    rates[currency] = defaults.get(currency, 1.0)

        # 加密貨幣匯率 (BTC/ETH 對 USD) - 這裡選擇在前端處理，或者後端統一轉 TWD
        # 為了簡化，資產管理通常以 TWD 總計，所以這裡只提供法幣匯率
        
        return jsonify({
            'rates': rates,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.warning(f'Exchange rate fetch failed: {e}')
        # 回傳預設值以防萬一
        return jsonify({
            'rates': {'TWD': 1.0, 'USD': 32.0, 'JPY': 0.21, 'HKD': 4.1, 'KRW': 0.024, 'VND': 0.0013},
            'timestamp': datetime.now().isoformat()
        })


@app.route('/api/risk-assessment')
def risk_assessment():
    return jsonify(portfolio.get_risk_assessment())

@app.route('/api/trades/analysis')
def trades_analysis():
    return jsonify(portfolio.get_trade_statistics())

@app.route('/api/signals')
def trading_signals():
    signals = market_data.get_signals(_watchlist)
    return jsonify({'signals': signals, 'timestamp': datetime.now().isoformat()})

@app.route('/')
def index():
    index_path = Path(__file__).parent.parent / 'ui' / 'public' / 'index.html'
    if index_path.exists():
        return index_path.read_text(encoding='utf-8')
    return '<h1>NoFOMO</h1><p>UI not found. Place index.html in ui/public/</p>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
