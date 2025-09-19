"""
AI Model Configuration System
Allows easy switching between different AI providers (Groq, Gemini, in-house) without code changes
"""

import os
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AIModelConfig:
    """Configuration for AI model providers"""
    
    # Available providers
    PROVIDERS = {
        'openai': {
            'name': 'OpenAI',
            'api_key_env': 'OPENAI_API_KEY',
            'api_url': 'https://api.openai.com/v1/chat/completions',
            'default_model': 'gpt-4o-mini',
            'models': ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo'],
            'rate_limit_handling': True,
            'fallback_support': True
        },
        'groq': {
            'name': 'Groq AI',
            'api_key_env': 'GROQ_API_KEY',
            'api_url': 'https://api.groq.com/openai/v1/chat/completions',
            'default_model': 'llama3-8b-8192',
            'models': ['llama3-8b-8192', 'llama3-70b-8192', 'mixtral-8x7b-32768', 'llama3.1-8b-instant', 'llama3.1-70b-versatile'],
            'rate_limit_handling': True,
            'fallback_support': True
        },
        'gemini': {
            'name': 'Google Gemini',
            'api_key_env': 'GEMINI_API_KEY',
            'api_url': 'https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent',
            'default_model': 'gemini-1.5-flash',
            'models': ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.5-pro-latest'],
            'rate_limit_handling': False,
            'fallback_support': True
        },
        'inhouse': {
            'name': 'In-House Model',
            'api_key_env': 'INHOUSE_API_KEY',
            'api_url_env': 'INHOUSE_API_URL',
            'default_model': 'custom-model',
            'models': ['custom-model'],
            'rate_limit_handling': False,
            'fallback_support': False
        }
    }
    
    def __init__(self):
        """Initialize AI model configuration"""
        self.custom_priority_order = None  # Store custom priority if set
        self.refresh_configuration()
    
    def refresh_configuration(self):
        """Force a complete refresh of the configuration"""
        # Re-detect the active provider from current environment
        self.active_provider = self._detect_active_provider()
        self.provider_config = self.PROVIDERS.get(self.active_provider, {})
        self._validate_config()
        logger.info(f"🔄 Configuration refreshed - Active provider: {self.active_provider}")
        
    def _detect_active_provider(self) -> str:
        """Detect which provider is currently configured"""
        # Priority order: OpenAI (reliable), Gemini (free tier), Groq, In-house
        if os.getenv('OPENAI_API_KEY'):
            logger.info("🎯 OpenAI API key detected - using OpenAI as primary provider")
            return 'openai'
        elif os.getenv('GEMINI_API_KEY'):
            logger.info("🎯 Gemini API key detected - using Gemini as primary provider")
            return 'gemini'
        elif os.getenv('GROQ_API_KEY'):
            logger.info("🎯 Groq API key detected - using Groq as primary provider")
            return 'groq'
        elif os.getenv('INHOUSE_API_KEY') and os.getenv('INHOUSE_API_URL'):
            logger.info("🎯 In-house model detected - using custom model as primary provider")
            return 'inhouse'
        else:
            logger.warning("⚠️ No AI provider configured - using fallback mode")
            return 'fallback'
    
    def _validate_config(self):
        """Validate the current provider configuration"""
        if self.active_provider == 'fallback':
            logger.warning("⚠️ Running in fallback mode - no AI capabilities available")
            return
            
        if not self.provider_config:
            logger.error(f"❌ Invalid provider: {self.active_provider}")
            self.active_provider = 'fallback'
            return
            
        api_key = os.getenv(self.provider_config.get('api_key_env', ''))
        if not api_key:
            logger.error(f"❌ API key not found for {self.active_provider}")
            self.active_provider = 'fallback'
            return
            
        logger.info(f"✅ {self.provider_config['name']} configured successfully")
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider"""
        if self.active_provider == 'fallback':
            return {
                'provider': 'fallback',
                'name': 'Fallback Mode',
                'status': 'no_ai_available',
                'models': [],
                'capabilities': ['basic_analysis', 'pattern_detection']
            }
        
        return {
            'provider': self.active_provider,
            'name': self.provider_config['name'],
            'status': 'active',
            'models': self.provider_config['models'],
            'capabilities': ['ai_analysis', 'intent_detection', 'sub_query_generation'],
            'rate_limit_handling': self.provider_config.get('rate_limit_handling', False),
            'fallback_support': self.provider_config.get('fallback_support', False)
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration for the current provider"""
        if self.active_provider == 'fallback':
            return {}
            
        config = {
            'api_key': os.getenv(self.provider_config['api_key_env']),
            'api_url': self.provider_config['api_url'],
            'default_model': self.provider_config['default_model']
        }
        
        # Handle in-house models with custom API URL
        if self.active_provider == 'inhouse':
            config['api_url'] = os.getenv('INHOUSE_API_URL', '')
            
        return config
    
    def is_available(self) -> bool:
        """Check if AI provider is available"""
        return self.active_provider != 'fallback'
    
    def get_fallback_providers(self) -> List[str]:
        """Get list of available fallback providers in priority order"""
        # Use custom priority order if set, otherwise use default
        if self.custom_priority_order:
            priority_order = self.custom_priority_order
        else:
            # Default priority order: Gemini (free tier), OpenAI, Groq (currently restricted)
            priority_order = ['gemini', 'openai', 'groq', 'inhouse']
        
        fallbacks = []
        
        for provider in priority_order:
            if provider != self.active_provider and provider in self.PROVIDERS:
                config = self.PROVIDERS[provider]
                if os.getenv(config['api_key_env']):
                    fallbacks.append(provider)
        
        return fallbacks
    
    def switch_provider(self, provider: str) -> bool:
        """Switch to a different provider"""
        if provider not in self.PROVIDERS:
            logger.error(f"❌ Invalid provider: {provider}")
            return False
            
        if not os.getenv(self.PROVIDERS[provider]['api_key_env']):
            logger.error(f"❌ API key not found for {provider}")
            return False
            
        self.active_provider = provider
        self.provider_config = self.PROVIDERS[provider]
        logger.info(f"🔄 Switched to {self.provider_config['name']}")
        return True
    
    def set_provider_priority(self, priority_list: List[str]) -> Dict[str, str]:
        """Set custom provider priority order"""
        available_providers = []
        unavailable_providers = []
        
        for provider in priority_list:
            if provider not in self.PROVIDERS:
                unavailable_providers.append(f"{provider} (invalid)")
                continue
                
            if not os.getenv(self.PROVIDERS[provider]['api_key_env']):
                unavailable_providers.append(f"{provider} (no API key)")
                continue
                
            available_providers.append(provider)
        
        if available_providers:
            # Set the first available provider as active
            old_provider = self.active_provider
            self.active_provider = available_providers[0]
            self.provider_config = self.PROVIDERS[self.active_provider]
            
            # Store the custom priority order
            self.custom_priority_order = available_providers
            
            logger.info(f"🎯 Priority updated: {' → '.join(available_providers)}")
            logger.info(f"🔄 Active provider: {old_provider} → {self.active_provider}")
            
            return {
                "status": "success",
                "active_provider": self.active_provider,
                "priority_order": available_providers,
                "unavailable": unavailable_providers
            }
        else:
            logger.error("❌ No valid providers in priority list")
            return {
                "status": "error",
                "message": "No valid providers available",
                "unavailable": unavailable_providers
            }
    
    def get_current_priority(self) -> Dict[str, Any]:
        """Get current provider priority information"""
        return {
            "active_provider": self.active_provider,
            "active_provider_name": self.provider_config.get('name', 'Unknown'),
            "fallback_providers": self.get_fallback_providers(),
            "all_providers": list(self.PROVIDERS.keys()),
            "available_providers": [p for p in self.PROVIDERS.keys() if os.getenv(self.PROVIDERS[p]['api_key_env'])]
        }

# Global instance
ai_config = AIModelConfig()
