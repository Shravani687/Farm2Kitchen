import google.generativeai as genai
from django.conf import settings

# PASTE YOUR KEY HERE
GOOGLE_API_KEY = "AIzaSyCoIaEm0ZDKS_QJQg1EqsQCHH_EnGbmaGA"

genai.configure(api_key=GOOGLE_API_KEY)

def get_gemini_response(user_question, context_data=""):
    try:
        # We are using the specific model from your valid list
        model = genai.GenerativeModel('gemini-flash-latest')
        
        system_instruction = """
        You are a helpful farming assistant for 'Farm2Kitchen'. 
        Your goal is to help farmers with prices, crops, and weather.
        
        Rules:
        1. Keep answers short (max 2-3 sentences).
        2. If the user asks in Hindi or Marathi, reply in that language.
        3. Be practical and encouraging.
        """
        
        full_prompt = f"{system_instruction}\n\nContext: {context_data}\n\nQuestion: {user_question}"
        
        response = model.generate_content(full_prompt)
        return response.text

    except Exception as e:
        return f"AI Service Error: {str(e)}"