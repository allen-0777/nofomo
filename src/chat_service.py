from typing import Dict, Any, Optional
from database import SessionLocal
from models import Settings
from parser_rule import RuleParser
from ai_agent import OpenAIAgent, GeminiAgent
import portfolio
import market_data
import logging

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.rule_parser = RuleParser()

    def _get_settings(self) -> Dict[str, str]:
        db = SessionLocal()
        settings = {}
        try:
            for s in db.query(Settings).all():
                settings[s.key] = s.value
        finally:
            db.close()
        return settings

    def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process user message, execute intent, and return result.
        """
        settings = self._get_settings()
        provider = settings.get("llm_provider", "NONE").upper()
        api_key = settings.get("api_key", "")
        model = settings.get("llm_model", "")

        intent = None
        source = "RULE"
        response_text = ""
        
        # 1. Try AI first if configured
        if provider in ["OPENAI", "GEMINI"] and api_key:
            try:
                agent = None
                if provider == "OPENAI":
                    agent = OpenAIAgent(api_key, model=model or "gpt-3.5-turbo")
                elif provider == "GEMINI":
                    agent = GeminiAgent(api_key, model=model or "gemini-1.5-flash")
                
                if agent:
                    ai_result = agent.chat(message)
                    response_text = ai_result.get('response', '')
                    tool_calls = ai_result.get('tool_calls', [])
                    
                    if tool_calls:
                        tc = tool_calls[0]
                        intent = {
                            'type': tc.get('action', 'UNKNOWN'),
                            'data': tc
                        }
                        source = "AI"
                    elif response_text:
                        # Chat only response
                        return {
                            'source': 'AI',
                            'response': response_text,
                            'intent': None,
                            'result': {'success': True, 'message': response_text}
                        }
            except Exception as e:
                logger.error(f"AI Agent failed: {e}. Fallback to Rule.")
                # Fallback to rule parser if AI fails
                source = "RULE_FALLBACK"

        # 2. Rule Parser (Fallback or Default)
        if not intent:
            intent = self.rule_parser.parse(message)
            if source == "RULE_FALLBACK":
                pass # Keep source as fallback
            else:
                source = "RULE"

        # 3. Execute Intent
        execution_result = self._execute_intent(intent)
        
        return {
            'source': source,
            'response': response_text,
            'intent': intent,
            'result': execution_result
        }

    def _execute_intent(self, intent: Dict) -> Dict:
        if not intent or intent.get('type') == 'UNKNOWN':
            return {'success': False, 'message': intent.get('error', '無法理解指令')}

        itype = intent.get('type')
        data = intent.get('data', {})

        try:
            if itype in ['BUY', 'SELL']:
                # 1. Enrich ticker symbol if missing
                if 'ticker' in data and 'ticker_symbol' not in data:
                    ticker = data['ticker']
                    # Simple heuristic
                    if ticker.isdigit() and len(ticker) >= 3: # TW stock
                        data['ticker_symbol'] = f"{ticker}.TW"
                        data['market'] = 'TW'
                    elif any(k in ticker.upper() for k in self.rule_parser.crypto_map): # Crypto
                         # Need strict match or lookup
                         for k, v in self.rule_parser.crypto_map.items():
                            if k == ticker.upper():
                                data['ticker_symbol'] = v
                                data['market'] = 'CRYPTO'
                                break
                    else: # Default to US
                        data['ticker_symbol'] = ticker.upper()
                        data['market'] = 'US'
                
                ticker_display = data.get('ticker')
                ticker_symbol = data.get('ticker_symbol', ticker_display)
                
                # 2. Fetch Market Data & Technical Analysis
                price_info = {}
                analysis_info = {}
                
                try:
                    price_info = market_data.get_stock_price(ticker_symbol)
                    analysis_info = market_data.technical_analysis(ticker_symbol)
                except Exception as e:
                    logger.error(f"Failed to fetch market data: {e}")

                # 3. Enrich Data for DB
                current_price = price_info.get('current_price', 0) if 'current_price' in price_info else 0
                
                # If manual price is not set, use current price
                if not data.get('price'):
                    data['price'] = current_price
                    data['entry_price'] = current_price
                
                # Calculate total amount
                qty = float(data.get('quantity', 0))
                price = float(data.get('price', 0))
                if not data.get('amount') and qty > 0 and price > 0:
                    data['amount'] = qty * price
                    data['total_value'] = qty * price

                # Add analysis data to trade record (but NO suggestion/score/targets)
                if analysis_info and 'error' not in analysis_info:
                    data.update({
                        'rsi': analysis_info.get('rsi'),
                        'trend': analysis_info.get('trend'),
                        'ma5': analysis_info.get('ma5'),
                        'ma20': analysis_info.get('ma20'),
                        'ma60': analysis_info.get('ma60'), # Added MA60
                        'macd': analysis_info.get('macd'),
                        # Explicitly NOT adding score, rating, suggestion, targets
                    })

                # 4. Save to DB
                trade_id = portfolio.add_trade(data)
                
                # 5. Generate Rich HTML Response (Removed Suggestions)
                action_text = "買入" if itype == 'BUY' else "賣出"
                color = "#10B981" if itype == 'BUY' else "#EF4444" # Green/Red
                currency = "NT$" if data.get('market') == 'TW' else "$"
                
                # Format numbers
                p_current = f"{currency}{current_price:,.2f}"
                p_entry = f"{currency}{price:,.2f}"
                
                # Market Tag
                market_tag = ""
                mkt = data.get('market', 'US')
                if mkt == 'TW': market_tag = '<span style="background:#E0F2FE;color:#0369A1;font-size:0.75rem;padding:2px 6px;border-radius:4px;font-weight:600">台股</span>'
                elif mkt == 'CRYPTO': market_tag = '<span style="background:#FEF3C7;color:#B45309;font-size:0.75rem;padding:2px 6px;border-radius:4px;font-weight:600">加密貨幣</span>'
                else: market_tag = '<span style="background:#F0FDF4;color:#166534;font-size:0.75rem;padding:2px 6px;border-radius:4px;font-weight:600">美股</span>'

                # Trend Color
                trend = data.get('trend', 'NEUTRAL')
                trend_color = '#10B981' if trend == 'BULLISH' else '#EF4444' if trend == 'BEARISH' else '#6B7280'
                trend_icon = '↑' if trend == 'BULLISH' else '↓' if trend == 'BEARISH' else '→'

                # MA values formatting
                ma5_val = f"{currency}{data.get('ma5', 0):,.2f}" if data.get('ma5') else "-"
                ma20_val = f"{currency}{data.get('ma20', 0):,.2f}" if data.get('ma20') else "-"
                ma60_val = f"{currency}{data.get('ma60', 0):,.2f}" if data.get('ma60') else "-"

                html_response = f"""
                <div style="font-size:0.95rem">
                  <div style="font-weight:700;font-size:1rem;margin-bottom:10px;color:{color}">✅ {action_text}記錄已儲存 (ID: {trade_id})</div>

                  <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:8px">
                    <span style="font-size:1.2rem;font-weight:700;color:#111">{ticker_display}</span>
                    {market_tag}
                    <span style="color:#6B7280;font-size:0.85rem">{price_info.get('name', '')}</span>
                    <span style="margin-left:auto;font-size:1.1rem;font-weight:700;color:#4F46E5">{p_current}</span>
                  </div>

                  <div style="background:#F8FAFF;border:1px solid #E8EDFF;border-radius:10px;padding:10px 14px;margin:8px 0">
                    <div style="font-weight:600;color:#4F46E5;font-size:0.85rem;margin-bottom:6px">📊 交易明細</div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">成交價格</span>
                        <span style="font-weight:500;font-size:0.9rem">{p_entry}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">成交股數</span>
                        <span style="font-weight:500;font-size:0.9rem">{qty} 股</span>
                    </div>
                  </div>

                  <div style="background:#F8FAFF;border:1px solid #E8EDFF;border-radius:10px;padding:10px 14px;margin:8px 0">
                    <div style="font-weight:600;color:#4F46E5;font-size:0.85rem;margin-bottom:6px">📈 技術指標</div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">RSI (14)</span>
                        <span style="font-weight:500;font-size:0.9rem">{data.get('rsi', 0):.1f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">趨勢</span>
                        <span style="font-weight:500;font-size:0.9rem;color:{trend_color}">{trend_icon} {trend}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">週線 (MA5)</span>
                        <span style="font-weight:500;font-size:0.9rem">{ma5_val}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">月線 (MA20)</span>
                        <span style="font-weight:500;font-size:0.9rem">{ma20_val}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">季線 (MA60)</span>
                        <span style="font-weight:500;font-size:0.9rem">{ma60_val}</span>
                    </div>
                  </div>
                </div>
                """
                
                return {'success': True, 'message': html_response}

            elif itype == 'CASH':
                trade_data = {
                    'action': data.get('action'),
                    'category': 'CASH',
                    'amount': data.get('amount'),
                    'currency': data.get('currency', 'TWD'),
                    'reason': data.get('reason')
                }
                trade_id = portfolio.add_trade(trade_data)
                
                # HTML for Cash
                is_deposit = data.get('action') == 'DEPOSIT'
                icon = '💰' if is_deposit else '💸'
                action_name = '存款' if is_deposit else '提款'
                color = '#10B981' if is_deposit else '#EF4444'
                amount_str = f"{data.get('currency')} {data.get('amount'):,.0f}"
                
                html_response = f"""
                <div style="font-size:0.95rem">
                  <div style="font-weight:700;font-size:1rem;margin-bottom:10px;color:{color}">{icon} {action_name}已記錄</div>
                  <div style="background:#F8FAFF;border:1px solid #E8EDFF;border-radius:10px;padding:10px 14px;margin:8px 0">
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">金額</span>
                        <span style="font-weight:700;font-size:0.9rem;color:{color}">{amount_str}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">說明</span>
                        <span style="font-weight:500;font-size:0.9rem">{data.get('reason','')}</span>
                    </div>
                  </div>
                  <div style="font-size:0.85rem;color:#6B7280;margin-top:5px">資產餘額已更新，請至統計頁查看。</div>
                </div>
                """
                return {'success': True, 'message': html_response}

            elif itype == 'ASSET':
                trade_data = {
                    'action': 'VALUATION',
                    'category': 'ASSET',
                    'asset_name': data.get('asset_name'),
                    'amount': data.get('amount'),
                    'currency': 'TWD',
                    'reason': data.get('reason')
                }
                trade_id = portfolio.add_trade(trade_data)
                
                # HTML for Asset
                html_response = f"""
                <div style="font-size:0.95rem">
                  <div style="font-weight:700;font-size:1rem;margin-bottom:10px;color:#4F46E5">🏠 資產估值已更新</div>
                  <div style="background:#F8FAFF;border:1px solid #E8EDFF;border-radius:10px;padding:10px 14px;margin:8px 0">
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">項目</span>
                        <span style="font-weight:500;font-size:0.9rem">{data.get('asset_name')}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">估值</span>
                        <span style="font-weight:700;font-size:0.9rem">NT$ {data.get('amount'):,.0f}</span>
                    </div>
                  </div>
                </div>
                """
                return {'success': True, 'message': html_response}

            elif itype == 'QUERY':
                # Query logic
                ticker = data.get('ticker')
                ticker_symbol = data.get('ticker_symbol') or ticker
                
                price_info = market_data.get_stock_price(ticker_symbol)
                analysis_info = market_data.technical_analysis(ticker_symbol)
                
                p_current = price_info.get('current_price', 0)
                currency = "NT$" if data.get('market') == 'TW' else "$"
                
                # Trend
                trend = analysis_info.get('trend', 'NEUTRAL')
                trend_color = '#10B981' if trend == 'BULLISH' else '#EF4444' if trend == 'BEARISH' else '#6B7280'
                
                # MA values formatting
                ma5_val = f"{currency}{analysis_info.get('ma5', 0):,.2f}" if analysis_info.get('ma5') else "-"
                ma20_val = f"{currency}{analysis_info.get('ma20', 0):,.2f}" if analysis_info.get('ma20') else "-"
                ma60_val = f"{currency}{analysis_info.get('ma60', 0):,.2f}" if analysis_info.get('ma60') else "-"

                html_response = f"""
                <div style="font-size:0.95rem">
                  <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:10px">
                    <span style="font-size:1.2rem;font-weight:700;color:#111">{ticker}</span>
                    <span style="color:#6B7280;font-size:0.85rem">{price_info.get('name', '')}</span>
                    <span style="margin-left:auto;font-size:1.1rem;font-weight:700;color:#4F46E5">{currency}{p_current:,.2f}</span>
                  </div>

                  <div style="background:#F8FAFF;border:1px solid #E8EDFF;border-radius:10px;padding:10px 14px;margin:8px 0">
                    <div style="font-weight:600;color:#4F46E5;font-size:0.85rem;margin-bottom:6px">📊 股價資訊</div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">52週高點</span>
                        <span style="font-weight:500;font-size:0.9rem">{currency}{price_info.get('week52_high', 0)}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">52週低點</span>
                        <span style="font-weight:500;font-size:0.9rem">{currency}{price_info.get('week52_low', 0)}</span>
                    </div>
                  </div>

                  <div style="background:#F8FAFF;border:1px solid #E8EDFF;border-radius:10px;padding:10px 14px;margin:8px 0">
                    <div style="font-weight:600;color:#4F46E5;font-size:0.85rem;margin-bottom:6px">📈 技術指標</div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">RSI (14)</span>
                        <span style="font-weight:500;font-size:0.9rem">{analysis_info.get('rsi', 0):.1f}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">趨勢</span>
                        <span style="font-weight:500;font-size:0.9rem;color:{trend_color}">{trend}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">週線 (MA5)</span>
                        <span style="font-weight:500;font-size:0.9rem">{ma5_val}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">月線 (MA20)</span>
                        <span style="font-weight:500;font-size:0.9rem">{ma20_val}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid rgba(0,0,0,0.06)">
                        <span style="color:#6B7280;font-size:0.85rem">季線 (MA60)</span>
                        <span style="font-weight:500;font-size:0.9rem">{ma60_val}</span>
                    </div>
                  </div>
                </div>
                """
                return {'success': True, 'message': html_response}

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {'success': False, 'message': f"執行失敗: {str(e)}"}

        return {'success': False, 'message': "未知的指令類型"}
