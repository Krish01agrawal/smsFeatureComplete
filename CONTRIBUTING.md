# Contributing to SMS Financial Insights Platform

Thank you for your interest in contributing to the SMS Financial Insights Platform! This document provides guidelines and information for contributors.

## 🎯 **How to Contribute**

### **Types of Contributions**

We welcome various types of contributions:

- **🐛 Bug Reports**: Help us identify and fix issues
- **✨ Feature Requests**: Suggest new features or improvements
- **📝 Documentation**: Improve documentation and guides
- **🧪 Testing**: Add tests and improve test coverage
- **🔧 Code Contributions**: Fix bugs, implement features
- **🎨 UI/UX Improvements**: Enhance user interface and experience

### **Getting Started**

1. **Fork the Repository**
   ```bash
   git clone https://github.com/yourusername/smsComplete.git
   cd smsComplete
   ```

2. **Set Up Development Environment**
   ```bash
   # Create virtual environments
   python -m venv extract-sms-email-data/venv
   python -m venv sms/venv
   
   # Install dependencies
   cd extract-sms-email-data && source venv/bin/activate && pip install -r requirements.txt
   cd ../sms && source venv/bin/activate && pip install -r requirements.txt
   ```

3. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 📋 **Contribution Guidelines**

### **Code Standards**

- **Python Style**: Follow PEP 8 guidelines
- **Type Hints**: Use type hints for better code clarity
- **Documentation**: Add docstrings for functions and classes
- **Testing**: Write tests for new features and bug fixes

### **Commit Message Format**

Use clear, descriptive commit messages:

```
feat: add new financial analytics endpoint
fix: resolve MongoDB connection timeout issue
docs: update API documentation for chat interface
test: add unit tests for transaction parser
refactor: improve error handling in SMS processor
```

### **Pull Request Process**

1. **Create Pull Request**
   - Use descriptive title and description
   - Reference related issues
   - Include screenshots for UI changes

2. **Code Review**
   - Ensure all tests pass
   - Follow code style guidelines
   - Address reviewer feedback

3. **Merge Process**
   - Squash commits if needed
   - Update documentation
   - Update CHANGELOG.md

## 🧪 **Testing Guidelines**

### **Running Tests**

```bash
# SMS Processing Module
cd extract-sms-email-data
python -m pytest tests/ -v

# Analytics Module
cd sms
python -m pytest tests/ -v

# Integration Tests
python -m pytest tests/integration/ -v
```

### **Test Coverage**

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test API endpoints and database operations
- **Performance Tests**: Test system performance and scalability
- **Security Tests**: Test security vulnerabilities

### **Writing Tests**

```python
import pytest
from unittest.mock import Mock, patch
from src.transaction_parser import TransactionParser

class TestTransactionParser:
    def test_parse_credit_transaction(self):
        """Test parsing of credit transaction SMS."""
        parser = TransactionParser()
        sms_data = {
            "sender": "VM-HDFCBK-S",
            "body": "A/c *1234 credited Rs.5000.00",
            "date": "2024-12-01T12:00:00Z"
        }
        
        result = parser.parse_sms_transaction(sms_data)
        
        assert result["transaction_type"] == "credit"
        assert result["amount"] == 5000.0
        assert result["currency"] == "INR"
```

## 📝 **Documentation Guidelines**

### **Code Documentation**

- **Docstrings**: Use Google-style docstrings
- **Comments**: Explain complex logic and algorithms
- **Type Hints**: Include type annotations

```python
def process_sms_data(sms_data: List[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
    """
    Process raw SMS data and extract financial transactions.
    
    Args:
        sms_data: List of SMS messages with sender, body, and date
        user_id: Unique identifier for the user
        
    Returns:
        Dictionary containing processing results and statistics
        
    Raises:
        ValueError: If SMS data format is invalid
        ConnectionError: If database connection fails
    """
    # Implementation here
```

### **API Documentation**

- **Endpoint Descriptions**: Clear descriptions of API endpoints
- **Request/Response Examples**: Include sample requests and responses
- **Error Codes**: Document all possible error responses

### **User Documentation**

- **Setup Guides**: Step-by-step installation instructions
- **Usage Examples**: Practical examples and use cases
- **Troubleshooting**: Common issues and solutions

## 🐛 **Bug Reports**

### **Before Reporting**

1. **Check Existing Issues**: Search for similar issues
2. **Test Latest Version**: Ensure you're using the latest version
3. **Reproduce Issue**: Create minimal reproduction steps

### **Bug Report Template**

```markdown
## Bug Description
Brief description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., macOS 14.0]
- Python Version: [e.g., 3.11.0]
- Module Version: [e.g., v2.0.0]

## Additional Context
Any additional information, screenshots, or logs
```

## ✨ **Feature Requests**

### **Feature Request Template**

```markdown
## Feature Description
Brief description of the feature

## Use Case
Why is this feature needed?

## Proposed Solution
How should this feature work?

## Alternatives Considered
Other solutions you've considered

## Additional Context
Any additional information or examples
```

## 🔧 **Development Setup**

### **Required Tools**

- **Python 3.8+**
- **MongoDB** (local or Atlas)
- **Git**
- **Code Editor** (VS Code, PyCharm, etc.)

### **Optional Tools**

- **Docker** (for containerized development)
- **Postman** (for API testing)
- **MongoDB Compass** (for database management)

### **Environment Configuration**

```bash
# Copy environment files
cp extract-sms-email-data/.env.example extract-sms-email-data/.env
cp sms/env_example.txt sms/.env

# Edit with your configuration
# MongoDB URI, API keys, etc.
```

## 📊 **Performance Guidelines**

### **Code Performance**

- **Database Queries**: Optimize MongoDB queries with proper indexing
- **Memory Usage**: Avoid memory leaks and excessive memory consumption
- **Response Times**: Keep API response times under 5 seconds
- **Caching**: Use appropriate caching strategies

### **Testing Performance**

```python
import time
import pytest
from src.financial_analyzer import FinancialAnalyzer

def test_analyzer_performance():
    """Test that financial analysis completes within acceptable time."""
    analyzer = FinancialAnalyzer()
    start_time = time.time()
    
    result = analyzer.analyze_user_data("user_123")
    
    execution_time = time.time() - start_time
    assert execution_time < 5.0  # Should complete within 5 seconds
```

## 🔒 **Security Guidelines**

### **Security Best Practices**

- **Input Validation**: Validate all user inputs
- **SQL Injection**: Use parameterized queries
- **Authentication**: Implement proper authentication
- **Secrets Management**: Never commit API keys or passwords

### **Security Testing**

```python
def test_input_validation():
    """Test that malicious inputs are properly handled."""
    parser = TransactionParser()
    
    # Test SQL injection attempt
    malicious_input = "'; DROP TABLE users; --"
    result = parser.parse_sms_transaction({"body": malicious_input})
    
    # Should not crash or execute malicious code
    assert result is not None
```

## 🎨 **UI/UX Guidelines**

### **Design Principles**

- **User-Friendly**: Intuitive and easy to use
- **Responsive**: Works on all device sizes
- **Accessible**: Follow accessibility guidelines
- **Consistent**: Maintain consistent design patterns

### **UI Components**

- **Streamlit Components**: Use consistent styling
- **Charts**: Use appropriate chart types for data
- **Colors**: Follow color accessibility guidelines
- **Typography**: Use readable fonts and sizes

## 📈 **Monitoring and Logging**

### **Logging Guidelines**

```python
import logging

logger = logging.getLogger(__name__)

def process_transaction(transaction_data):
    """Process transaction with proper logging."""
    logger.info(f"Processing transaction: {transaction_data['id']}")
    
    try:
        result = parse_transaction(transaction_data)
        logger.info(f"Transaction processed successfully: {result['id']}")
        return result
    except Exception as e:
        logger.error(f"Failed to process transaction: {e}")
        raise
```

### **Monitoring**

- **Performance Metrics**: Track response times and throughput
- **Error Rates**: Monitor error rates and failures
- **Resource Usage**: Monitor CPU, memory, and database usage
- **User Activity**: Track user engagement and usage patterns

## 🤝 **Community Guidelines**

### **Code of Conduct**

- **Be Respectful**: Treat all contributors with respect
- **Be Constructive**: Provide constructive feedback
- **Be Patient**: Be patient with new contributors
- **Be Collaborative**: Work together to improve the project

### **Communication**

- **GitHub Issues**: Use for bug reports and feature requests
- **GitHub Discussions**: Use for general questions and discussions
- **Pull Requests**: Use for code contributions and reviews

## 🏆 **Recognition**

### **Contributor Recognition**

- **Contributors List**: Added to README.md
- **Release Notes**: Mentioned in release notes
- **Special Thanks**: Recognition for significant contributions

### **Contributor Levels**

- **🥉 Bronze**: First contribution (bug fix, documentation)
- **🥈 Silver**: Multiple contributions (features, improvements)
- **🥇 Gold**: Major contributions (architecture, core features)
- **💎 Diamond**: Core maintainer (review, mentoring)

## 📚 **Resources**

### **Documentation**

- **API Documentation**: [API_GUIDE.md](extract-sms-email-data/docs/API_GUIDE.md)
- **Chat API Guide**: [FINANCIAL_CHAT_API_GUIDE.md](sms/docs/FINANCIAL_CHAT_API_GUIDE.md)
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Security Guide**: [SECURITY.md](SECURITY.md)

### **External Resources**

- **Python Style Guide**: [PEP 8](https://pep8.org/)
- **FastAPI Documentation**: [FastAPI Docs](https://fastapi.tiangolo.com/)
- **Streamlit Documentation**: [Streamlit Docs](https://docs.streamlit.io/)
- **MongoDB Documentation**: [MongoDB Docs](https://docs.mongodb.com/)

## ❓ **Questions?**

If you have questions about contributing:

1. **Check Documentation**: Review existing documentation
2. **Search Issues**: Look for similar questions in issues
3. **Create Discussion**: Start a GitHub discussion
4. **Contact Maintainers**: Reach out to project maintainers

---

**Thank you for contributing to the SMS Financial Insights Platform! 🎉**

Your contributions help make this platform better for everyone. Whether you're fixing a bug, adding a feature, or improving documentation, every contribution matters.

**Happy Coding! 🚀**
