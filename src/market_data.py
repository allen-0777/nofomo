import time
import threading
import logging
from typing import Dict, Optional, Any
from analyzer import (
    get_stock_price as _fetch_price,
    technical_analysis as _compute_analysis,
    get_stock_history as _get_stock_history,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 內存快取（附鎖）
# ---------------------------------------------------------------------------
_price_cache: Dict[str, Any] = {}
_cache_lock = threading.Lock()
_cache_ttl_price = 60      # 60 秒
_cache_ttl_analysis = 300  # 5 分鐘

def _get_cached(ticker: str, cache_type: str = 'price') -> Optional[Any]:
    key = f"{cache_type}:{ticker.upper()}"
    with _cache_lock:
        if key in _price_cache:
            data, timestamp = _price_cache[key]
            ttl = _cache_ttl_analysis if cache_type == 'analysis' else _cache_ttl_price
            if time.time() - timestamp < ttl:
                return data
    return None

def _set_cached(ticker: str, cache_type: str, data: Any):
    key = f"{cache_type}:{ticker.upper()}"
    with _cache_lock:
        _price_cache[key] = (data, time.time())

def clear_cache():
    with _cache_lock:
        _price_cache.clear()
    logger.info('Cache cleared')

def get_stock_price(ticker: str) -> Dict:
    """取得即時股價（帶快取）"""
    cached = _get_cached(ticker, 'price')
    if cached:
        logger.info(f'Cache hit: {ticker}')
        return cached
    
    result = _fetch_price(ticker)
    if 'error' not in result:
        _set_cached(ticker, 'price', result)
    return result

def technical_analysis(ticker: str) -> Dict:
    """技術分析（帶快取，並展平 MACD dict 以維持 API 相容性）"""
    cached = _get_cached(ticker, 'analysis')
    if cached:
        logger.info(f'Analysis cache hit: {ticker}')
        return cached

    result = _compute_analysis(ticker)
    if 'error' not in result:
        # 將 analyzer.py 回傳的 macd dict 展平，保持原有 API 格式
        macd_data = result.get('macd', {})
        if isinstance(macd_data, dict):
            result['macd'] = macd_data.get('macd')
            result['macd_signal'] = macd_data.get('signal')
            result['macd_histogram'] = macd_data.get('histogram')
            result['macd_crossover'] = macd_data.get('crossover')
        _set_cached(ticker, 'analysis', result)

    return result

def get_signals(watchlist: list) -> list:
    """產生交易訊號"""
    signals = []
    _SUGGESTION_MAP = {5: '強烈買入', 4: '偏多買入', 3: '觀察等待', 2: '謹慎操作', 1: '不建議'}

    # 限制數量避免太久
    for ticker in watchlist[:10]:
        try:
            analysis = technical_analysis(ticker)
            if 'error' in analysis:
                continue

            rsi = analysis.get('rsi') or 0.0
            score = analysis.get('score', 3)

            signal = {
                'ticker': ticker,
                'price': analysis.get('current_price'),
                'trend': analysis.get('trend'),
                'rsi': round(float(rsi), 1),
                'score': score,
                'suggestion': _SUGGESTION_MAP.get(score, '觀察等待'),
            }

            if rsi < 30 and analysis.get('trend') == 'BULLISH':
                signal['action'] = '強烈買入'
            elif rsi < 40:
                signal['action'] = '考慮買入'
            elif rsi > 70:
                signal['action'] = '考慮賣出'
            else:
                signal['action'] = '觀望'

            signals.append(signal)
        except Exception as e:
            logger.error(f'Signal error: {ticker} {e}')
    
    return signals

def get_stock_history(ticker: str, period: str = '1mo'):
    return _get_stock_history(ticker, period)

def get_cache_stats() -> Dict:
    with _cache_lock:
        return {
            'size': len(_price_cache),
            'ttl': {'price': _cache_ttl_price, 'analysis': _cache_ttl_analysis}
        }
