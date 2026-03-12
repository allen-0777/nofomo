import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# OpenAI Tools Schema
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "record_trade",
            "description": "Record a new trade (buy/sell/deposit/withdraw/valuation)",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["BUY", "SELL", "DEPOSIT", "WITHDRAW", "VALUATION"]},
                    "ticker": {"type": "string", "description": "Stock ticker e.g. TSLA, 2330.TW"},
                    "quantity": {"type": "number"},
                    "price": {"type": "number", "description": "Transaction price per share"},
                    "amount": {"type": "number", "description": "Total amount for cash transactions or asset valuation"},
                    "currency": {"type": "string", "enum": ["USD", "TWD"]},
                    "asset_name": {"type": "string", "description": "Name of asset for VALUATION"},
                    "reason": {"type": "string"}
                },
                "required": ["action"]
            }
        }
    }
]

class AIAgent(ABC):
    @abstractmethod
    def chat(self, message: str) -> Dict:
        """
        Process message and return result.
        Returns: { 'response': str, 'tool_calls': List[Dict] }
        """
        pass

class OpenAIAgent(AIAgent):
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self.model = model
        except ImportError:
            logger.error("openai module not found")
            raise ImportError("Please install openai package")

    def chat(self, message: str) -> Dict:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful trading assistant. Extract trade details from user messages."},
                    {"role": "user", "content": message}
                ],
                tools=OPENAI_TOOLS,
                tool_choice="auto"
            )
            
            msg = completion.choices[0].message
            tool_calls = []
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.function.name == "record_trade":
                        try:
                            args = json.loads(tc.function.arguments)
                            tool_calls.append(args)
                        except:
                            pass
            
            return {
                'response': msg.content,
                'tool_calls': tool_calls
            }
        except Exception as e:
            logger.error(f"OpenAI Error: {e}")
            return {'response': f"Error: {str(e)}", 'tool_calls': []}

class GeminiAgent(AIAgent):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # Gemini Tool Definition
            self.tools_def = {
                "function_declarations": [{
                    "name": "record_trade",
                    "description": "Record a new trade",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "action": {"type": "STRING", "description": "BUY, SELL, DEPOSIT, WITHDRAW, VALUATION"},
                            "ticker": {"type": "STRING", "description": "Stock ticker e.g. TSLA, 2330.TW"},
                            "quantity": {"type": "NUMBER"},
                            "price": {"type": "NUMBER"},
                            "amount": {"type": "NUMBER"},
                            "currency": {"type": "STRING", "description": "USD or TWD"},
                            "asset_name": {"type": "STRING"},
                            "reason": {"type": "STRING"}
                        },
                        "required": ["action"]
                    }
                }]
            }
            
            self.client = genai.GenerativeModel(model, tools=[self.tools_def])

        except ImportError:
            logger.error("google-generativeai module not found")
            raise ImportError("Please install google-generativeai package")

    def chat(self, message: str) -> Dict:
        try:
            response = self.client.generate_content(message)
            tool_calls = []
            
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        fc = part.function_call
                        if fc.name == "record_trade":
                            # Convert Map to dict
                            args = {}
                            for k, v in fc.args.items():
                                args[k] = v
                            tool_calls.append(args)
            
            # Safe text extraction
            text_response = ""
            try:
                text_response = response.text
            except:
                pass # response.text fails if there's no text part
                
            return {
                'response': text_response,
                'tool_calls': tool_calls
            }
        except Exception as e:
            logger.error(f"Gemini Error: {e}")
            return {'response': f"Error: {str(e)}", 'tool_calls': []}
