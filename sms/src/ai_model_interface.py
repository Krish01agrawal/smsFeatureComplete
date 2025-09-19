"""
Unified AI Model Interface
Provides a consistent API for different AI providers (Groq, Gemini, in-house)
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional
import requests
from .ai_model_config import ai_config

logger = logging.getLogger(__name__)

class AIModelInterface:
    """Unified interface for different AI model providers"""
    
    def __init__(self):
        """Initialize the AI model interface"""
        self._refresh_config()
    
    def _refresh_config(self):
        """Refresh configuration from the latest config"""
        # Force a complete refresh of the AI config
        self.config = ai_config
        self.config.refresh_configuration()
        self.provider = self.config.active_provider
        self.api_config = self.config.get_api_config()
        
    def call_ai_model(self, messages: List[Dict[str, str]], 
                      model: Optional[str] = None, 
                      temperature: float = 0.1, 
                      max_tokens: int = 800,
                      max_retries: int = 1) -> Optional[str]:
        """
        Unified method to call any AI model
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model name (uses default if not specified)
            temperature: Creativity level (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            max_retries: Number of retry attempts
            
        Returns:
            AI response text or None if failed
        """
        # Refresh config to ensure we use the latest provider priority
        self._refresh_config()
        
        # Log the current priority order for debugging
        logger.info(f"🎯 AI Provider Priority: {self.provider} → {self.config.get_fallback_providers()}")
        
        if not self.config.is_available():
            logger.warning("⚠️ No AI provider available - using fallback")
            return self._fallback_response(messages)
        
        # Use default model if none specified
        if not model:
            model = self.api_config.get('default_model', 'default')
        
        # Route to appropriate provider with detailed logging
        logger.info(f"🚀 Attempting {self.provider.upper()} API call...")
        
        if self.provider == 'openai':
            return self._call_openai_api(messages, model, temperature, max_tokens, max_retries)
        elif self.provider == 'groq':
            return self._call_groq_api(messages, model, temperature, max_tokens, max_retries)
        elif self.provider == 'gemini':
            return self._call_gemini_api(messages, model, temperature, max_tokens, max_retries)
        elif self.provider == 'inhouse':
            return self._call_inhouse_api(messages, model, temperature, max_tokens, max_retries)
        else:
            return self._fallback_response(messages)
    
    def _call_openai_api(self, messages: List[Dict[str, str]], 
                         model: str, temperature: float, 
                         max_tokens: int, max_retries: int) -> Optional[str]:
        """Call OpenAI API with rate limit handling"""
        logger.info("🔵 OpenAI API: Starting request...")
        api_key = self.api_config['api_key']
        api_url = self.api_config['api_url']
        
        for attempt in range(max_retries + 1):
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "messages": messages,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                }
                
                response = requests.post(api_url, headers=headers, json=data, timeout=120)
                
                if response.status_code == 429:  # Rate limit
                    if attempt < max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"OpenAI rate limited, waiting {wait_time}s before retry {attempt + 1}")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.warning("OpenAI rate limit exceeded, trying fallback")
                        return self._try_fallback_provider(messages, model, temperature, max_tokens)
                
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning("🔵 OpenAI rate limit hit, trying fallback")
                    return self._try_fallback_provider(messages, model, temperature, max_tokens)
                else:
                    logger.error(f"🔵 OpenAI API call failed: {e}")
                    logger.error(f"🔵 Response status: {e.response.status_code}")
                    logger.error(f"🔵 Response body: {e.response.text}")
                    return self._try_fallback_provider(messages, model, temperature, max_tokens)
            except Exception as e:
                logger.error(f"OpenAI API call failed: {e}")
                return None
        
        return None
    
    def _call_groq_api(self, messages: List[Dict[str, str]], 
                       model: str, temperature: float, 
                       max_tokens: int, max_retries: int) -> Optional[str]:
        """Call Groq API with rate limit handling"""
        logger.info("🟠 Groq API: Starting request...")
        api_key = self.api_config['api_key']
        api_url = self.api_config['api_url']
        
        for attempt in range(max_retries + 1):
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "messages": messages,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                }
                
                response = requests.post(api_url, headers=headers, json=data, timeout=20)
                
                if response.status_code == 429:  # Rate limit
                    if attempt < max_retries:
                        wait_time = 1
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.warning("Rate limit exceeded, trying fallback")
                        return self._try_fallback_provider(messages, model, temperature, max_tokens)
                
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning("Rate limit hit, trying fallback")
                    return self._try_fallback_provider(messages, model, temperature, max_tokens)
                else:
                    logger.error(f"Groq API call failed: {e}")
                    logger.error(f"Response status: {e.response.status_code}")
                    logger.error(f"Response body: {e.response.text}")
                    return None
            except Exception as e:
                logger.error(f"Groq API call failed: {e}")
                return None
        
        return None
    
    def _call_gemini_api(self, messages: List[Dict[str, str]], 
                         model: str, temperature: float, 
                         max_tokens: int, max_retries: int) -> Optional[str]:
        """Call Google Gemini API"""
        logger.info("🟢 Gemini API: Starting request...")
        api_key = self.api_config['api_key']
        api_url = self.api_config['api_url']
        
        # Convert OpenAI format to Gemini format
        gemini_messages = self._convert_to_gemini_format(messages)
        
        for attempt in range(max_retries + 1):
            try:
                headers = {
                    "Content-Type": "application/json"
                }
                
                # Gemini API parameters - updated for v1 API
                data = {
                    "contents": gemini_messages,
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens,
                        "topP": 0.8,
                        "topK": 40
                    },
                    "safetySettings": [
                        {
                            "category": "HARM_CATEGORY_HARASSMENT",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                        },
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                        }
                    ]
                }
                
                # Add API key to URL for Gemini
                url_with_key = f"{api_url}?key={api_key}"
                response = requests.post(url_with_key, headers=headers, json=data, timeout=120)
                
                if response.status_code == 429:  # Rate limit
                    if attempt < max_retries:
                        wait_time = 2
                        logger.warning(f"Gemini rate limited, waiting {wait_time}s before retry {attempt + 1}")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.warning("Gemini rate limit exceeded, trying fallback")
                        return self._try_fallback_provider(messages, model, temperature, max_tokens)
                
                response.raise_for_status()
                result = response.json()
                
                # Extract text from Gemini response - updated for v1 API
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0].get('content', {})
                    if 'parts' in content and len(content['parts']) > 0:
                        return content['parts'][0].get('text', '')
                
                logger.warning("Unexpected Gemini response format")
                return None
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning("Gemini rate limit hit, trying fallback")
                    return self._try_fallback_provider(messages, model, temperature, max_tokens)
                else:
                    logger.error(f"Gemini API call failed: {e}")
                    logger.error(f"Response status: {e.response.status_code}")
                    logger.error(f"Response body: {e.response.text}")
                    return None
            except Exception as e:
                logger.error(f"Gemini API call failed: {e}")
                return None
        
        return None
    
    def _call_inhouse_api(self, messages: List[Dict[str, str]], 
                          model: str, temperature: float, 
                          max_tokens: int, max_retries: int) -> Optional[str]:
        """Call in-house model API"""
        api_key = self.api_config.get('api_key')
        api_url = self.api_config.get('api_url')
        
        if not api_url:
            logger.error("In-house API URL not configured")
            return None
        
        for attempt in range(max_retries + 1):
            try:
                headers = {
                    "Content-Type": "application/json"
                }
                
                # Add API key to headers if provided
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                
                # Assume in-house API follows OpenAI format
                data = {
                    "messages": messages,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                response = requests.post(api_url, headers=headers, json=data, timeout=120)
                response.raise_for_status()
                result = response.json()
                
                # Try to extract response (adapt based on your in-house API format)
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content']
                elif 'response' in result:
                    return result['response']
                elif 'text' in result:
                    return result['text']
                else:
                    logger.warning("Unexpected in-house API response format")
                    return None
                    
            except Exception as e:
                logger.error(f"In-house API call failed: {e}")
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                return None
        
        return None
    
    def _convert_to_gemini_format(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Convert OpenAI format messages to Gemini format"""
        gemini_messages = []
        
        for message in messages:
            role = message['role']
            content = message['content']
            
            # Map OpenAI roles to Gemini roles
            if role == 'system':
                # Gemini doesn't have system messages, prepend to user message
                if gemini_messages and gemini_messages[-1]['role'] == 'user':
                    gemini_messages[-1]['parts'][0]['text'] = f"{content}\n\n{gemini_messages[-1]['parts'][0]['text']}"
                else:
                    # Create a user message with system content
                    gemini_messages.append({
                        "role": "user",
                        "parts": [{"text": content}]
                    })
            elif role == 'user':
                gemini_messages.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role == 'assistant':
                gemini_messages.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
        
        return gemini_messages
    
    def _try_fallback_provider(self, messages: List[Dict[str, str]], 
                              model: str, temperature: float, 
                              max_tokens: int) -> Optional[str]:
        """Try to use a fallback provider if available (prevents infinite loops)"""
        # Prevent infinite recursion by tracking attempted providers
        if not hasattr(self, '_attempted_providers'):
            self._attempted_providers = set()
        
        # Mark current provider as attempted
        self._attempted_providers.add(self.provider)
        
        fallback_providers = self.config.get_fallback_providers()
        
        for provider in fallback_providers:
            # Skip if we've already tried this provider
            if provider in self._attempted_providers:
                continue
                
            logger.info(f"🔄 Trying fallback provider: {provider}")
            if self.config.switch_provider(provider):
                self.provider = provider
                self.api_config = self.config.get_api_config()
                self._attempted_providers.add(provider)
                
                # Call the specific provider method directly to avoid recursion
                if provider == 'openai':
                    result = self._call_openai_api(messages, model, temperature, max_tokens, max_retries=0)
                elif provider == 'gemini':
                    result = self._call_gemini_api(messages, model, temperature, max_tokens, max_retries=0)
                elif provider == 'groq':
                    result = self._call_groq_api(messages, model, temperature, max_tokens, max_retries=0)
                else:
                    result = None
                
                if result:
                    # Clear attempted providers on success
                    self._attempted_providers.clear()
                    return result
        
        logger.warning("All fallback providers exhausted")
        self._attempted_providers.clear()
        return self._fallback_response(messages)
    
    def _fallback_response(self, messages: List[Dict[str, str]]) -> str:
        """Provide a basic fallback response when no AI is available"""
        # Extract the last user message
        user_message = ""
        for message in reversed(messages):
            if message['role'] == 'user':
                user_message = message['content']
                break
        
        # Simple keyword-based responses
        query_lower = user_message.lower()
        
        if any(word in query_lower for word in ['salary', 'income', 'earnings']):
            return "I can help analyze your salary patterns. Please check your transaction data for income entries."
        elif any(word in query_lower for word in ['expense', 'spending', 'cost']):
            return "I can help analyze your spending patterns. Please check your transaction data for expense entries."
        elif any(word in query_lower for word in ['pattern', 'trend', 'analysis']):
            return "I can help identify patterns in your financial data. Please provide specific transaction details."
        else:
            return "I'm currently in fallback mode. Please check your AI provider configuration or try again later."
    
    def get_status(self) -> Dict[str, Any]:
        """Get current AI model status"""
        return {
            'provider': self.provider,
            'available': self.config.is_available(),
            'provider_info': self.config.get_provider_info(),
            'fallback_providers': self.config.get_fallback_providers()
        }

# Global instance
ai_interface = AIModelInterface()
