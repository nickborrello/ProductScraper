# LLM Product Classification

This document describes the new LLM-based product classification system that replaces the inconsistent hybrid AI + fuzzy matching approach.

## Overview

The LLM classifier uses OpenAI's GPT-4o-mini API to provide accurate, consistent product classification with persistent context. It maintains a conversation thread to remember the comprehensive pet product taxonomy across all classifications.

## Setup

1. **Get OpenAI API Key**: Sign up at [OpenAI](https://platform.openai.com/) and get an API key
2. **Configure Settings**:
   - Copy `settings.example.json` to `settings.json`
   - Add your OpenAI API key: `"openai_api_key": "your_key_here"`
   - Set classification method: `"classification_method": "llm"`

## Classification Methods

- **hybrid** (default): AI model + fuzzy matching fallback
- **llm**: OpenAI GPT API only (most accurate)
- **fuzzy**: Fuzzy matching only (fastest, least accurate)

## Cost Estimate

- **Monthly Cost**: ~$0.70 for 1000 product classifications
- **API Model**: GPT-4o-mini ($0.15/1M input tokens, $0.60/1M output tokens)
- **Typical Usage**: 50-100 tokens per classification

## Features

- **Persistent Context**: Conversation thread maintains full product taxonomy
- **Comprehensive Taxonomy**: Covers all pet types, food categories, and product types
- **Consistent Results**: Same product always gets same classification
- **Fallback Support**: Gracefully falls back to hybrid method if API fails
- **Batch Processing**: Efficiently processes multiple products

## Taxonomy Coverage

The system includes comprehensive categories for:
- Dog, Cat, Bird, Fish, Reptile, and Small Pet products
- Food, treats, toys, healthcare, grooming, beds, bowls
- All major product pages

## Usage

```python
from src.core.classification.classifier import classify_single_product

# Classify with LLM
product = {
    'Name': 'Purina Pro Plan Adult Dog Food Chicken & Rice',
    'Brand': 'Purina'
}

result = classify_single_product(product, method="llm")
print(result['Category'])  # "Dog Food"
print(result['Product Type'])  # "Dry Dog Food|Wet Dog Food"
print(result['Product On Pages'])  # "Dog Food Shop All|Brand Pages"
```

## Settings UI

Configure the classification method and API key through the Settings dialog in the main application (⚙️ Application tab → AI/ML Settings).