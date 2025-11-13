# Chrome DevTools Integration for ProductScraper

This guide explains how to use Chrome DevTools MCP server to debug your Selenium scrapers in real-time.

## 🚀 Quick Start

1. **Enable DevTools in your scraper:**

   ```bash
   python devtools_setup.py enable-devtools
   ```

2. **Configure MCP to connect to Selenium:**

   ```bash
   python devtools_setup.py connect-selenium
   ```

3. **Restart VS Code** to apply MCP configuration changes.

4. **Run your scraper** - it will now enable remote debugging on port 9222.

5. **Use MCP commands** in Copilot Chat to debug:
   ```
   Navigate to https://www.coastalpet.com/products/search/?q=076484648649
   Take a screenshot of the current page
   Evaluate JavaScript: document.querySelectorAll('div.product-listing').length
   ```

## 🔧 How It Works

When `ENABLE_DEVTOOLS = True` in your scraper:

1. **Selenium launches Chrome** with `--remote-debugging-port=9222`
2. **MCP server connects** to the same Chrome instance via `http://127.0.0.1:9222`
3. **You can debug live** while your scraper runs

## 🛠️ Available Commands

### Setup Commands

```bash
# Enable DevTools in coastal.py
python devtools_setup.py enable-devtools

# Disable DevTools in coastal.py
python devtools_setup.py disable-devtools

# Configure MCP to connect to Selenium Chrome
python devtools_setup.py connect-selenium

# Configure MCP for standalone Chrome
python devtools_setup.py standalone
```

### MCP Debug Commands (in Copilot Chat)

#### Navigation

```
Navigate to https://www.coastalpet.com/products/search/?q=YOUR_SKU
Navigate back in history
Navigate forward in history
Reload the current page
```

#### Page Inspection

```
Take a screenshot of the current page
List all pages currently open
Select page by index (e.g., select_page 0)
```

#### Element Analysis

```
Evaluate JavaScript: document.querySelectorAll('div.product-listing').length
Evaluate JavaScript: document.querySelector('p.product-listing__title--text a')?.textContent
Evaluate JavaScript: document.querySelector('img.product-listing__product-image--image')?.src
```

#### Network Monitoring

```
List all network requests
Get details for network request by index
```

#### Console & Debugging

```
List all console messages
Take a snapshot of the current page
Evaluate JavaScript: console.log('Debug from MCP')
```

#### Input Automation

```
Click on element with selector: p.product-listing__title--text a
Fill input with selector: #search-input value: YOUR_SKU
Press key: Enter
```

## 🔍 Debugging Your Coastal Scraper

### Step-by-Step Debug Process:

1. **Enable DevTools:**

   ```bash
   python devtools_setup.py enable-devtools
   python devtools_setup.py connect-selenium
   ```

2. **Run your scraper:**

   ```bash
   cd src/scrapers
   python coastal.py
   ```

3. **While scraper runs, debug in Copilot Chat:**

   **Check if page loaded:**

   ```
   Evaluate JavaScript: document.title
   Take a screenshot of the current page
   ```

   **Test your selectors:**

   ```
   Evaluate JavaScript: document.querySelectorAll('div.product-listing').length
   ```

   **If selectors work, inspect the content:**

   ```
   Evaluate JavaScript:
   const elem = document.querySelector('p.product-listing__title--text a');
   elem ? elem.textContent.trim() : 'Element not found'
   ```

   **Check for images:**

   ```
   Evaluate JavaScript:
   const img = document.querySelector('img.product-listing__product-image--image');
   img ? img.getAttribute('src') : 'Image not found'
   ```

4. **Monitor network requests:**
   ```
   List all network requests
   ```
   This helps identify if the page is making AJAX calls for dynamic content.

## ⚙️ Configuration Options

### In Your Scraper

```python
HEADLESS = False          # Keep visible for debugging
ENABLE_DEVTOOLS = True    # Enable remote debugging
DEBUG_MODE = True         # Enable scraper debug pauses
```

### MCP Configuration

The `.vscode/mcp.json` is automatically managed by `devtools_setup.py`.

For manual configuration:

```json
{
  "servers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "-y",
        "chrome-devtools-mcp@latest",
        "--browserUrl=http://127.0.0.1:9222"
      ]
    }
  }
}
```

## 🔧 Advanced Usage

### Custom DevTools Port

If port 9222 conflicts, modify the browser creation:

```python
create_browser("Coastal Pet", headless=HEADLESS, enable_devtools=True, devtools_port=9223)
```

And update MCP config:

```json
{
  "servers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "-y",
        "chrome-devtools-mcp@latest",
        "--browserUrl=http://127.0.0.1:9223"
      ]
    }
  }
}
```

### Multiple Scrapers

Each scraper can have its own DevTools port:

- Coastal: port 9222
- Amazon: port 9223
- etc.

### Performance Analysis

```
Start performance trace
Navigate to your target page
Stop performance trace
```

This gives you detailed performance insights.

## 🐛 Troubleshooting

### MCP Server Won't Connect

1. Check if your scraper is running with `ENABLE_DEVTOOLS = True`
2. Verify Chrome is listening on port 9222: visit `http://127.0.0.1:9222/json`
3. Restart VS Code after changing MCP configuration

### Scraper Runs But No Debug Connection

1. Check console for "devtools=true" in browser initialization message
2. Ensure no firewall blocks port 9222
3. Try a different port if 9222 is in use

### Performance Issues

- DevTools adds overhead, so disable when not debugging
- Use `HEADLESS = True` with DevTools for faster testing

## 📚 Resources

- [Chrome DevTools MCP Documentation](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [Chrome Remote Debugging](https://developer.chrome.com/docs/devtools/remote-debugging/)
- [MCP Protocol](https://modelcontextprotocol.io/)
