# AI Model Management System Guide - Production v2.0

## 🎯 Overview

The Production API v2.0 features an advanced AI model management system that allows seamless switching between different AI providers (Groq, Gemini, In-house models) with automatic fallback, health monitoring, and real-time provider switching capabilities.

## 🚀 Features

- **Automatic Provider Detection**: Automatically detects which AI provider is configured
- **Seamless Switching**: Switch between providers without restarting the API
- **Fallback Support**: Automatically falls back to available providers if one fails
- **Unified Interface**: Same API calls work with any provider
- **Rate Limit Handling**: Built-in rate limit handling and retry logic
- **Future-Proof**: Easy to add new providers or in-house models

## 🔧 Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Gemini (Recommended - Free tier available)
GEMINI_API_KEY=your_gemini_api_key_here

# Groq (Alternative)
GROQ_API_KEY=your_groq_api_key_here

# In-house Model (Optional)
INHOUSE_API_KEY=your_inhouse_api_key_here
INHOUSE_API_URL=http://localhost:5000/v1/chat/completions
```

### Provider Priority

The system automatically selects providers in this order:
1. **Gemini** (if `GEMINI_API_KEY` is set)
2. **Groq** (if `GROQ_API_KEY` is set)
3. **In-house** (if both `INHOUSE_API_KEY` and `INHOUSE_API_URL` are set)
4. **Fallback mode** (if no providers are configured)

## 📱 Production API v2.0 Endpoints

### Get AI Provider Status
```bash
GET /ai/providers
```

Response:
```json
{
  "current_provider": {
    "provider": "gemini",
    "name": "Google Gemini",
    "status": "active",
    "models": ["gemini-pro", "gemini-pro-vision"],
    "capabilities": ["ai_analysis", "intent_detection", "sub_query_generation"]
  },
  "available_providers": ["groq"],
  "all_providers": {...}
}
```

### Switch AI Provider
```bash
POST /ai/switch/{provider}
```

**Parameters:**
- `provider`: groq, gemini, or inhouse

Response:
```json
{
  "success": true,
  "message": "Switched to gemini",
  "current_provider": {...}
}
```

### Health Check
```bash
GET /health
```

## 🛠️ Management Commands

### List All Providers
```bash
python3 manage_ai_providers.py list
```

### Switch Provider
```bash
python3 manage_ai_providers.py switch gemini
python3 manage_ai_providers.py switch groq
```

### Check Environment Configuration
```bash
python3 manage_ai_providers.py env
```

### Show Help
```bash
python3 manage_ai_providers.py help
```

## 🔄 Switching Between Providers

### Method 1: API Call
```bash
curl -X POST "http://localhost:8000/switch-ai-provider?provider=gemini"
```

### Method 2: Management Script
```bash
python3 manage_ai_providers.py switch gemini
```

### Method 3: Environment Variable Change
1. Update your `.env` file
2. Restart the API server
3. The system will automatically detect the new configuration

## 🎯 Use Cases

### 1. Groq Quota Exhausted → Switch to Gemini
```bash
# When Groq quota is exhausted
python3 manage_ai_providers.py switch gemini
```

### 2. Testing Different Models
```bash
# Test Gemini
python3 manage_ai_providers.py switch gemini

# Test Groq
python3 manage_ai_providers.py switch groq
```

### 3. Production Deployment
```bash
# Use in-house model for production
export INHOUSE_API_KEY=prod_key
export INHOUSE_API_URL=https://your-model.com/v1/chat/completions
python3 run_api.py
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │───▶│ AI Model Config  │───▶│ Provider Logic  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       ▼
         │                       │              ┌─────────────────┐
         │                       │              │ Unified Interface│
         │                       │              └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MongoDB       │    │   Environment    │    │   Fallback      │
│   Connection    │    │   Variables      │    │   Responses     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔍 Troubleshooting

### Common Issues

#### 1. "No AI provider configured"
**Solution**: Add API keys to your `.env` file
```bash
GEMINI_API_KEY=your_key_here
```

#### 2. "Rate limit exceeded"
**Solution**: The system automatically tries fallback providers

#### 3. "Failed to switch provider"
**Solution**: Check if the API is running and the provider is configured

### Debug Commands

```bash
# Check current status
python3 manage_ai_providers.py list

# Check environment
python3 manage_ai_providers.py env

# Check API health
curl http://localhost:8000/health
```

## 🚀 Adding New Providers

To add a new AI provider:

1. **Update `ai_model_config.py`**:
```python
'new_provider': {
    'name': 'New Provider',
    'api_key_env': 'NEW_PROVIDER_API_KEY',
    'api_url': 'https://api.newprovider.com/v1/chat/completions',
    'default_model': 'new-model',
    'models': ['new-model'],
    'rate_limit_handling': True,
    'fallback_support': True
}
```

2. **Update `ai_model_interface.py`**:
```python
elif self.provider == 'new_provider':
    return self._call_new_provider_api(messages, model, temperature, max_tokens, max_retries)
```

3. **Add the API call method**:
```python
def _call_new_provider_api(self, messages, model, temperature, max_tokens, max_retries):
    # Implementation for new provider
    pass
```

## 📊 Performance Comparison

| Provider | Speed | Cost | Rate Limits | Fallback |
|----------|-------|------|-------------|----------|
| Gemini   | Medium| Free | High        | ✅       |
| Groq     | Fast  | Paid | Medium      | ✅       |
| In-house | Fast  | Free | None        | ❌       |

## 🔐 Security Notes

- API keys are stored in environment variables
- Never commit API keys to version control
- Use `.env` files for local development
- Use secure environment variables in production

## 📚 Examples

### Complete Workflow

1. **Start with Gemini**:
```bash
export GEMINI_API_KEY=your_key
python3 run_api.py
```

2. **Switch to Groq when needed**:
```bash
python3 manage_ai_providers.py switch groq
```

3. **Check status**:
```bash
python3 manage_ai_providers.py list
```

4. **Monitor health**:
```bash
curl http://localhost:8000/health
```

### Environment File Example

```bash
# .env
OPENAI_API_KEY=openai_api_key
GEMINI_API_KEY=gemini_api_key
GROQ_API_KEY=groq_api_key
MONGODB_URI=db_url
```

## 🎉 Benefits

✅ **Zero Code Changes**: Switch providers without modifying your application code
✅ **Automatic Fallback**: System automatically handles provider failures
✅ **Easy Management**: Simple commands to switch and monitor providers
✅ **Future-Proof**: Easy to add new providers or in-house models
✅ **Cost Optimization**: Use free tiers when available, paid when needed
✅ **Production Ready**: Built-in error handling and monitoring

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify your environment configuration
3. Check the API logs for detailed error messages
4. Use the management script to diagnose issues

---

**Happy AI Model Management! 🚀**

*Last Updated: Production API v2.0 - December 2024*
*Endpoints Updated: All endpoints reflect current v2.0 API structure*
