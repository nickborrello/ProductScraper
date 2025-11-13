# Local LLM Classification with Ollama

ProductScraper now supports running Large Language Models locally using [Ollama](https://ollama.com), eliminating the need for API keys and reducing costs.

## What is Ollama?

Ollama is a tool that allows you to run open-source LLMs locally on your machine. It supports models like Llama, Gemma, Phi, and many others.

## Benefits

- ✅ **No API Keys Required** - Run models locally without external dependencies
- 💰 **Cost Free** - No API usage costs
- 🔒 **Private** - All processing happens locally
- 🚀 **Fast** - Once models are downloaded, classification is quick
- 📱 **Offline Capable** - Works without internet after initial setup

## Installation

### Option 1: Automated Setup (Recommended)

Run the included setup script:

```bash
python scripts/setup_ollama.py
```

This script will:

- Detect your operating system
- Download and install Ollama
- Pull the default model (llama3.2)
- Verify the installation

### Option 2: Manual Installation

1. Visit [ollama.com/download](https://ollama.com/download)
2. Download and install Ollama for your platform
3. Start Ollama: `ollama serve`
4. Pull a model: `ollama pull llama3.2`

## Configuration

1. Open ProductScraper settings
2. Go to the "⚙️ Application" tab
3. In the "AI/ML Settings" section:
   - Set "Classification Method" to `local_llm`
   - Set "Ollama Model" to your preferred model (default: `llama3.2`)

## Available Models

Some recommended models for product classification:

| Model    | Size | Use Case                 | Command                   |
| -------- | ---- | ------------------------ | ------------------------- |
| llama3.2 | 3B   | Fast, good quality       | `ollama pull llama3.2`    |
| llama3.2 | 1B   | Very fast, basic quality | `ollama pull llama3.2:1b` |
| gemma3   | 4B   | Good balance             | `ollama pull gemma3`      |
| phi4     | 14B  | High quality             | `ollama pull phi4`        |

## System Requirements

- **RAM**: At least 8GB (16GB recommended for larger models)
- **Storage**: 2-20GB free space depending on model size
- **Platform**: Windows, macOS, or Linux

## Usage

Once configured, product classification will use your local Ollama model instead of external APIs. The interface remains the same - just select products and classify them as usual.

## Troubleshooting

### Ollama Not Found

```
Error: Ollama not available. Please install Ollama and ensure it's running
```

**Solution**: Run `ollama serve` in a terminal, or use the setup script.

### Model Not Available

```
Error: model 'xyz' not found
```

**Solution**: Pull the model first: `ollama pull <model_name>`

### Slow Performance

- Try a smaller model (e.g., `llama3.2:1b`)
- Ensure you have enough RAM
- Close other memory-intensive applications

### Port Already in Use

```
Error: listen tcp 127.0.0.1:11434: bind: address already in use
```

**Solution**: Kill existing Ollama process or change the port in Ollama settings.

## Advanced Configuration

### Custom Models

Create custom models with specific prompts:

```bash
# Create a Modelfile
echo "FROM llama3.2
SYSTEM \"You are a product classification expert. Always respond in JSON format.\"
PARAMETER temperature 0.1" > Modelfile

# Create the model
ollama create product-classifier -f Modelfile
```

Then set "Ollama Model" to `product-classifier` in settings.

### Environment Variables

You can also set the model via environment variables:

```bash
export OLLAMA_MODEL=llama3.2
python main.py
```

## Performance Comparison

| Method         | Speed  | Cost | Privacy  | Setup  |
| -------------- | ------ | ---- | -------- | ------ |
| OpenRouter API | Fast   | Paid | External | Easy   |
| Local Ollama   | Medium | Free | Local    | Medium |
| Fuzzy Matching | Fast   | Free | Local    | None   |

Choose based on your needs:

- **Speed**: Use OpenRouter API
- **Privacy/Cost**: Use Local Ollama
- **Reliability**: Use Fuzzy Matching (fallback)
