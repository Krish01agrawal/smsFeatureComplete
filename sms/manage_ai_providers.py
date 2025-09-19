#!/usr/bin/env python3
"""
AI Provider Management Script
Easily switch between different AI providers (Groq, Gemini, In-house)
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AIProviderManager:
    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.providers = {
            'groq': {
                'name': 'Groq AI',
                'env_key': 'GROQ_API_KEY',
                'description': 'Fast inference with Llama models'
            },
            'gemini': {
                'name': 'Google Gemini',
                'env_key': 'GEMINI_API_KEY',
                'description': 'Google\'s advanced AI model (free tier available)'
            },
            'inhouse': {
                'name': 'In-House Model',
                'env_key': 'INHOUSE_API_KEY',
                'url_env': 'INHOUSE_API_URL',
                'description': 'Your own hosted model'
            }
        }
    
    def check_api_status(self):
        """Check if the API is running"""
        try:
            response = requests.get(f"{self.api_base}/health", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.exceptions.RequestException:
            return None
    
    def list_providers(self):
        """List all available AI providers and their status"""
        print("🤖 AI Provider Status")
        print("=" * 50)
        
        # Check API status
        api_status = self.check_api_status()
        if not api_status:
            print("❌ API is not running. Start it with: python3 run_api.py")
            return
        
        current_provider = api_status['services']['ai_model']
        print(f"🎯 Current Provider: {current_provider['name']} ({current_provider['provider']})")
        print(f"📊 Status: {current_provider['status']}")
        print()
        
        print("📋 Available Providers:")
        for provider_id, provider_info in self.providers.items():
            env_key = provider_info['env_key']
            api_key = os.getenv(env_key)
            
            status_icon = "✅" if api_key else "❌"
            status_text = "Configured" if api_key else "Not configured"
            
            print(f"  {status_icon} {provider_info['name']}: {status_text}")
            print(f"     Description: {provider_info['description']}")
            
            if provider_id == 'inhouse':
                url_env = provider_info.get('url_env')
                if url_env:
                    url = os.getenv(url_env)
                    if url:
                        print(f"     API URL: {url}")
                    else:
                        print(f"     API URL: Not set")
            
            print()
    
    def switch_provider(self, provider_id):
        """Switch to a different AI provider"""
        if provider_id not in self.providers:
            print(f"❌ Invalid provider: {provider_id}")
            print(f"Available providers: {', '.join(self.providers.keys())}")
            return False
        
        provider_info = self.providers[provider_id]
        env_key = provider_info['env_key']
        api_key = os.getenv(env_key)
        
        if not api_key:
            print(f"❌ {provider_info['name']} API key not found in environment")
            print(f"Please set {env_key} in your .env file")
            return False
        
        # Check if API is running
        api_status = self.check_api_status()
        if not api_status:
            print("❌ API is not running. Start it with: python3 run_api.py")
            return False
        
        try:
            response = requests.post(f"{self.api_base}/switch-ai-provider", 
                                   params={"provider": provider_id}, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Successfully switched to {provider_info['name']}")
                print(f"📊 New status: {result['current_provider']['name']}")
                return True
            else:
                print(f"❌ Failed to switch provider: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error connecting to API: {e}")
            return False
    
    def show_usage(self):
        """Show usage information"""
        print("🚀 AI Provider Management Script")
        print("=" * 40)
        print()
        print("Usage:")
        print("  python3 manage_ai_providers.py list          - List all providers and status")
        print("  python3 manage_ai_providers.py switch <id>   - Switch to provider")
        print("  python3 manage_ai_providers.py help          - Show this help")
        print()
        print("Examples:")
        print("  python3 manage_ai_providers.py switch gemini - Switch to Gemini")
        print("  python3 manage_ai_providers.py switch groq   - Switch to Groq")
        print()
        print("Available providers:")
        for provider_id, provider_info in self.providers.items():
            print(f"  {provider_id}: {provider_info['name']}")
    
    def check_env_file(self):
        """Check and display .env file configuration"""
        print("🔧 Environment Configuration Check")
        print("=" * 40)
        
        env_file = ".env"
        if not os.path.exists(env_file):
            print(f"❌ {env_file} file not found")
            return
        
        print(f"📁 Found {env_file} file")
        print()
        
        for provider_id, provider_info in self.providers.items():
            env_key = provider_info['env_key']
            api_key = os.getenv(env_key)
            
            if api_key:
                # Mask the API key for security
                masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
                print(f"✅ {env_key}: {masked_key}")
            else:
                print(f"❌ {env_key}: Not set")
            
            if provider_id == 'inhouse':
                url_env = provider_info.get('url_env')
                if url_env:
                    url = os.getenv(url_env)
                    if url:
                        print(f"✅ {url_env}: {url}")
                    else:
                        print(f"❌ {url_env}: Not set")
        
        print()
        print("💡 To configure a provider:")
        print("   1. Add the API key to your .env file")
        print("   2. Restart the API server")
        print("   3. Use 'switch' command to activate it")

def main():
    manager = AIProviderManager()
    
    if len(sys.argv) < 2:
        manager.show_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        manager.list_providers()
    elif command == "switch":
        if len(sys.argv) < 3:
            print("❌ Please specify a provider ID")
            print("Example: python3 manage_ai_providers.py switch gemini")
            return
        provider_id = sys.argv[2].lower()
        manager.switch_provider(provider_id)
    elif command == "env":
        manager.check_env_file()
    elif command in ["help", "--help", "-h"]:
        manager.show_usage()
    else:
        print(f"❌ Unknown command: {command}")
        manager.show_usage()

if __name__ == "__main__":
    main()
