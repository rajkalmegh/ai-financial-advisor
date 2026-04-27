import os
from dotenv import load_dotenv

load_dotenv()

# Try importing Groq
try:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    USE_AI = True
except:
    USE_AI = False

def fallback_advice(summary, total, avg):
    if not summary:
        return "Start tracking expenses to get advice."

    max_cat = max(summary, key=summary.get)

    advice = f"""
💡 Basic Financial Advice:

- You are spending most on {max_cat}
- Try reducing this category by 20%
- Daily average spend: ₹{avg}

Action Plan:
Cut unnecessary expenses and aim to save at least 20% of your income.
"""
    return advice


def chat_with_advisor(messages, expense_summary, total, avg):
    
    if not USE_AI or not os.getenv("GROQ_API_KEY"):
        return fallback_advice(expense_summary, total, avg)

    system_prompt = f"""
You are a strict financial advisor.

User expense data:
{expense_summary}

Total spend: ₹{total}
Daily avg: ₹{avg}

Give short, actionable advice.
"""

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=full_messages
        )
        return response.choices[0].message.content

    except Exception as e:
        return fallback_advice(expense_summary, total, avg)