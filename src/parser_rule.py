import re
from typing import Dict, Optional, Tuple

class RuleParser:
    def __init__(self):
        self.crypto_map = {
            'BTC': 'BTC-USD', '比特幣': 'BTC-USD',
            'ETH': 'ETH-USD', '以太幣': 'ETH-USD', '以太坊': 'ETH-USD',
            'USDT': 'USDT-USD', '泰達幣': 'USDT-USD',
            'SOL': 'SOL-USD', 'BNB': 'BNB-USD', 'XRP': 'XRP-USD', 'DOGE': 'DOGE-USD'
        }

    def _parse_number(self, text: str) -> Optional[float]:
        """
        Parse number with units (e.g., '10萬', '1.5k', '200')
        """
        if not text:
            return None
        
        # Remove commas
        text = text.replace(',', '')
        
        # Multipliers
        multiplier = 1.0
        if '萬' in text or 'w' in text.lower():
            multiplier = 10000.0
            text = re.sub(r'[萬wW]', '', text)
        elif '億' in text:
            multiplier = 100000000.0
            text = text.replace('億', '')
        elif 'k' in text.lower():
            multiplier = 1000.0
            text = re.sub(r'[kK]', '', text)
            
        try:
            val = float(text)
            return val * multiplier
        except ValueError:
            return None

    def parse(self, msg: str) -> Dict:
        """
        Parse natural language message into a structured intent.
        Returns: { 'type': 'BUY'|'SELL'|'QUERY'|'CASH'|'ASSET'|'UNKNOWN', 'data': {...} }
        """
        msg_upper = msg.upper()
        msg_lower = msg.lower()

        # 1. Crypto Parsing
        crypto_symbol = None
        crypto_display = None
        for key, val in self.crypto_map.items():
            if key in msg_upper: 
                crypto_symbol = val
                crypto_display = key
                break
        
        # 2. Stock Ticker Parsing
        # Use msg_upper to handle lowercase inputs, but filter out keywords
        ignored_keywords = {
            'BUY', 'SELL', 'GET', 'PUT', 'CALL', 'ASK', 'BID', 
            'LOW', 'HIGH', 'OPEN', 'CLOSE', 'VOL', 'VOLUME',
            'RSI', 'MACD', 'MA', 'EMA', 'SMA', 'KD',
            'THE', 'AND', 'FOR', 'WITH', 'FROM', 'THAT', 'THIS',
            'USD', 'TWD', 'HKD', 'JPY', 'KRW', 'CNY', 'EUR',
            'STOCK', 'SHARE', 'SHARES', 'PRICE', 'COST', 'DATE', 'TIME',
            'ANALYSIS', 'ANALYZE', 'QUERY', 'CHECK', 'FIND', 'SEARCH',
            'CHART', 'PLOT', 'SHOW', 'VIEW', 'LOOK', 'SEE',
            'OF', 'AT', 'IN', 'ON', 'TO', 'BY', 'UP', 'DO', 'GO', 
            'IS', 'IT', 'MY', 'ME', 'WE', 'HE', 'SHE', 'NO', 'OK',
            'HI', 'HELLO', 'HEY', 'YO',
            'A', 'I'
        }
        
        us_candidates = re.findall(r'\b([A-Z]{1,5})\b', msg_upper)
        us_ticker = None
        for cand in us_candidates:
            if cand not in ignored_keywords:
                us_ticker = cand
                break

        tw_match = re.search(r'(?<![.$])\b(\d{3,6})\b(?!\s*[股張])', msg)

        ticker_display = None
        ticker_symbol = None
        market = None
        
        if crypto_symbol:
            ticker_symbol = crypto_symbol
            ticker_display = crypto_display
            market = 'CRYPTO'
        elif us_ticker:
            ticker_display = us_ticker
            ticker_symbol = ticker_display
            market = 'US'
        elif tw_match:
            ticker_display = tw_match.group(1)
            ticker_symbol = f"{ticker_display}.TW"
            market = 'TW'

        # 3. Quantity Parsing
        # Try to find specific quantity pattern first: number + unit
        # Pattern: (digits)[spaces](unit)
        qty_match = re.search(r'(\d+(?:\.\d+)?)\s*([股張顆個])', msg)
        
        quantity = 1.0
        if qty_match:
            raw_num = float(qty_match.group(1))
            unit = qty_match.group(2)
            # Handle '張' (sheet/lot) = 1000 shares for TW stocks
            # Convention: if user explicitly says '張', it means lots.
            # User requested to remove 'Zhang' logic and stick to shares.
            # So we treat everything as shares.
            quantity = raw_num
        else:
            # Fallback: find a number that isn't the ticker
            all_nums = re.findall(r'\d+(?:\.\d+)?', msg)
            for num in all_nums:
                # Skip if it looks like the ticker
                if tw_match and num == tw_match.group(1):
                    continue
                try:
                    quantity = float(num)
                    break
                except: pass
        
        # 4. Price Parsing
        # "賣@500", "sell at 100", "price 50", "50元"
        # Regex: (prefix) (number)(unit?)
        price_match = re.search(r'(?:賣|sell|@|\$|price)\s*(\d+(?:\.\d+)?[萬wWkK]?)', msg, re.IGNORECASE)
        manual_price = None
        if price_match:
            manual_price = self._parse_number(price_match.group(1))

        # 5. Intent Classification
        
        # CASH (Deposit/Withdraw)
        # "存 10萬", "deposit 5k"
        deposit_match = re.search(r'(?:存|deposit|入金)\s*(\d+(?:\.\d+)?[萬wWkK]?)', msg, re.IGNORECASE)
        withdraw_match = re.search(r'(?:領|提|withdraw|出金)\s*(\d+(?:\.\d+)?[萬wWkK]?)', msg, re.IGNORECASE)
        
        if deposit_match or withdraw_match:
            raw_amount = (deposit_match or withdraw_match).group(1)
            amount = self._parse_number(raw_amount)
            
            is_deposit = bool(deposit_match)
            is_usd = '美金' in msg_lower or 'usd' in msg_lower or '$' in msg
            currency = 'USD' if is_usd else 'TWD'
            
            return {
                'type': 'CASH',
                'data': {
                    'action': 'DEPOSIT' if is_deposit else 'WITHDRAW',
                    'amount': amount,
                    'currency': currency,
                    'reason': msg
                }
            }

        # ASSET Valuation
        # "房子 值 2000萬"
        asset_match = re.search(r'(.+?)\s*(?:值|value)\s*(\d+(?:\.\d+)?[萬wWkK]?)', msg, re.IGNORECASE)
        if asset_match and '買' not in msg and '賣' not in msg and 'buy' not in msg_lower and 'sell' not in msg_lower:
            asset_name = asset_match.group(1).replace('資產', '').replace('我的', '').replace('這個', '').strip()
            raw_val = asset_match.group(2)
            amount = self._parse_number(raw_val)
            
            return {
                'type': 'ASSET',
                'data': {
                    'action': 'VALUATION',
                    'asset_name': asset_name,
                    'amount': amount,
                    'reason': msg
                }
            }

        # BUY
        if '買' in msg or 'buy' in msg_lower:
            if not ticker_symbol:
                return {'type': 'UNKNOWN', 'error': '找不到股票代號'}
            return {
                'type': 'BUY',
                'data': {
                    'action': 'BUY',
                    'ticker': ticker_display,
                    'ticker_symbol': ticker_symbol,
                    'market': market,
                    'quantity': quantity,
                    'price': manual_price, 
                    'reason': msg
                }
            }

        # SELL
        if '賣' in msg or 'sell' in msg_lower:
            if not ticker_symbol:
                return {'type': 'UNKNOWN', 'error': '找不到股票代號'}
            return {
                'type': 'SELL',
                'data': {
                    'action': 'SELL',
                    'ticker': ticker_display,
                    'ticker_symbol': ticker_symbol,
                    'market': market,
                    'quantity': quantity,
                    'price': manual_price,
                    'reason': msg
                }
            }

        # QUERY / ANALYZE
        if ticker_symbol and any(x in msg_lower for x in ['股價', '分析', '多少', '看', '查', 'analyze', 'price', 'quote']):
            return {
                'type': 'QUERY',
                'data': {
                    'ticker': ticker_display,
                    'ticker_symbol': ticker_symbol,
                    'market': market
                }
            }

        return {'type': 'UNKNOWN'}
