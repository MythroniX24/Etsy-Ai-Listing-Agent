import os
import json
import requests
import telebot
from typing import Dict, Any, List
from openai import OpenAI

# ==========================================
# 1. ETSY API HANDLER
# ==========================================
class EtsyStoreManager:
    def __init__(self):
        self.api_key = os.getenv("ETSY_API_KEY")
        self.shop_id = os.getenv("ETSY_SHOP_ID")
        self.access_token = os.getenv("ETSY_ACCESS_TOKEN")
        self.base_url = "https://openapi.etsy.com/v3/application"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

    def create_draft_listing(self, title: str, description: str, price: float, quantity: int, tags: List[str]) -> Dict[str, Any]:
        url = f"{self.base_url}/shops/{self.shop_id}/listings"
        payload = {
            "title": title[:140], 
            "description": description,
            "price": price,
            "quantity": quantity,
            "who_made": "i_did",
            "when_made": "2020_2026",
            "taxonomy_id": "1", # Default taxonomy (Modify as needed)
            "state": "draft",
            "is_supply": "false",
            "tags": ",".join(tags[:13])
        }
        try:
            response = requests.post(url, headers=self._get_headers(), data=payload)
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

    def get_shop_analytics(self) -> Dict[str, Any]:
        url = f"{self.base_url}/shops/{self.shop_id}/receipts"
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()
            total_sales = data.get("count", 0)
            results = data.get("results", [])
            total_revenue = sum(float(r.get("grandtotal", {}).get("amount", 0)) / r.get("grandtotal", {}).get("divisor", 1) for r in results)
            
            return {
                "status": "success", 
                "total_sales": total_sales,
                "revenue": total_revenue,
                "currency": results[0].get("grandtotal", {}).get("currency_code", "USD") if results else "USD"
            }
        except requests.exceptions.RequestException as e:
             return {"status": "error", "message": str(e)}

# ==========================================
# 2. AI AGENT ORCHESTRATOR
# ==========================================
class EtsyAIAgent:
    def __init__(self):
        self.llm_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.etsy_manager = EtsyStoreManager()
        self.model_name = "openai/gpt-4o" 
        
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "create_draft_listing",
                    "description": "Create a new draft product listing on Etsy. Generate SEO optimized title, tags, and description.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "SEO optimized product title (max 140 chars)."},
                            "description": {"type": "string", "description": "Detailed product description."},
                            "price": {"type": "number", "description": "Price of the product."},
                            "quantity": {"type": "integer", "description": "Number of items in stock."},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Array of 13 SEO tags."}
                        },
                        "required": ["title", "description", "price", "quantity", "tags"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_shop_analytics",
                    "description": "Fetch the shop's sales and revenue analytics."
                }
            }
        ]

    def execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> str:
        if function_name == "create_draft_listing":
            result = self.etsy_manager.create_draft_listing(**arguments)
            return json.dumps(result)
        elif function_name == "get_shop_analytics":
            result = self.etsy_manager.get_shop_analytics()
            return json.dumps(result)
        return json.dumps({"error": "Function not found."})

    def run(self, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": "You are an expert Etsy store manager. Help the user manage their store. Speak clearly in Hinglish. When you create a listing or check stats, confirm it enthusiastically."},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                messages.append(response_message)
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    function_response = self.execute_tool(function_name, function_args)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    })
                
                second_response = self.llm_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages
                )
                return second_response.choices[0].message.content
            else:
                return response_message.content
                
        except Exception as e:
            return f"❌ Error: {str(e)}"

# ==========================================
# 3. TELEGRAM BOT SETUP
# ==========================================
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
if not bot_token:
    print("⚠️ WARNING: TELEGRAM_BOT_TOKEN missing.")

bot = telebot.TeleBot(bot_token)
agent = EtsyAIAgent()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Namaste! 🙏 Main aapka AI Etsy Manager hu. Mujhe bataiye aapko kya list karna hai ya apne store ka data dekhna hai?")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Send a "typing..." action so the user knows it's working
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Process the prompt through our AI Agent
    reply_text = agent.run(message.text)
    
    # Send the final response back to Telegram
    bot.reply_to(message, reply_text)

if __name__ == "__main__":
    print("🚀 Telegram Bot is running! Waiting for messages...")
    bot.infinity_polling()
      
