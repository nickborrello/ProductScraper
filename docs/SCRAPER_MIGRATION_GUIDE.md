# Scraper Migration Guide

This guide provides step-by-step instructions for migrating from the legacy monolithic scraper system to the new modular YAML-based scraper system.

## Overview

The new modular scraper system replaces the old monolithic Python files with:

- **YAML Configuration Files**: Declarative scraper definitions
- **WorkflowExecutor**: Unified execution engine
- **Anti-Detection Manager**: Built-in anti-detection capabilities
- **Modular Architecture**: Reusable components and easier maintenance

## Migration Process

### Step 1: Analyze Legacy Scraper

Identify the key components of your legacy scraper:

```python
# Legacy scraper structure (example from src/scrapers_archive/archive/amazon.py)
def scrape_amazon(skus, log_callback=None, progress_tracker=None, status_callback=None):
    # Browser initialization
    browser_context = init_browser_optimized("amazon_batch", headless=HEADLESS)

    # Main scraping loop
    for sku in skus:
        product_info = scrape_single_product(sku, driver, log_callback=log_callback)
        # Process results...

def scrape_single_product(UPC_or_ASIN, driver, max_retries=0, log_callback=None):
    # Navigation logic
    search_url = f"https://www.amazon.com/s?k={UPC_or_ASIN}"
    driver.get(search_url)

    # Element interaction
    _click_first_search_result(driver, log_callback=log_callback)

    # Data extraction
    _extract_product_data(driver, product_info, log_callback=log_callback)
```

### Step 2: Create YAML Configuration

Convert the legacy logic into a YAML configuration file:

```yaml
# New modular configuration (src/scrapers/configs/amazon.yaml)
name: "amazon"
base_url: "https://www.amazon.com"
timeout: 30
retries: 3

selectors:
  - name: "product_name"
    selector: "#productTitle"
    attribute: "text"
  - name: "brand"
    selector: "#bylineInfo, #brand, .a-brand"
    attribute: "text"
  - name: "images"
    selector: "#altImages li.imageThumbnail img"
    attribute: "src"
    multiple: true

workflows:
  - action: "navigate"
    params:
      url: "https://www.amazon.com/s?k={sku}"
  - action: "wait_for"
    params:
      selector: ".s-result-item"
      timeout: 10
  - action: "click"
    params:
      selector: ".s-result-item a.a-link-normal[href*='/dp/']"
  - action: "wait_for"
    params:
      selector: "#productTitle"
      timeout: 10
  - action: "extract"
    params:
      fields: ["product_name", "brand", "images"]

anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  enable_blocking_handling: true
  rate_limit_min_delay: 1.0
  rate_limit_max_delay: 5.0
```

### Step 3: Update Integration Code

Replace legacy scraper calls with the new WorkflowExecutor:

```python
# Before: Legacy scraper usage
from src.scrapers_archive.archive.amazon import scrape_amazon

results = scrape_amazon(skus, log_callback=log_callback)

# After: New modular scraper usage
from src.scrapers.parser.yaml_parser import YAMLParser
from src.scrapers.executor.workflow_executor import WorkflowExecutor

# Load configuration
parser = YAMLParser()
config = parser.parse("src/scrapers/configs/amazon.yaml")

# Execute workflow
executor = WorkflowExecutor(config, headless=True)
results = executor.execute_workflow()
```

### Step 4: Handle Anti-Detection Features

The new system includes built-in anti-detection capabilities. Configure them in the YAML:

```yaml
anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  enable_session_rotation: false
  enable_blocking_handling: true
  captcha_selectors:
    - "[class*='captcha']"
    - "[id*='captcha']"
  blocking_selectors:
    - "[class*='blocked']"
    - "[id*='blocked']"
  rate_limit_min_delay: 1.0
  rate_limit_max_delay: 5.0
```

### Step 5: Update Error Handling

The new system provides structured error handling:

```python
# Before: Manual error handling
try:
    result = scrape_single_product(sku, driver)
except Exception as e:
    display_error(f"Error scraping {sku}: {e}", log_callback=log_callback)
    result = None

# After: WorkflowExecutor handles errors automatically
try:
    results = executor.execute_workflow()
    if not results["success"]:
        logger.error(f"Workflow failed: {results.get('error')}")
except WorkflowExecutionError as e:
    logger.error(f"Execution failed: {e}")
```

## Configuration Mapping Guide

### Browser Initialization

| Legacy | New System |
|--------|------------|
| `init_browser_optimized()` | `create_browser()` in WorkflowExecutor |
| Manual profile management | Automatic profile management |
| Custom Chrome options | Standardized browser creation |

### Navigation Logic

| Legacy | New System |
|--------|------------|
| `driver.get(url)` | `action: "navigate"` |
| Manual URL construction | Template variables in YAML |
| Custom wait logic | `action: "wait_for"` |

### Element Interaction

| Legacy | New System |
|--------|------------|
| `driver.find_element().click()` | `action: "click"` |
| `driver.find_element().send_keys()` | `action: "input_text"` |
| Manual element finding | CSS selector configuration |

### Data Extraction

| Legacy | New System |
|--------|------------|
| Custom extraction functions | `action: "extract"` |
| Manual attribute parsing | Selector configuration |
| Complex parsing logic | Built-in attribute extraction |

### Error Handling

| Legacy | New System |
|--------|------------|
| Manual try/catch blocks | WorkflowExecutionError |
| Custom retry logic | Built-in retry mechanism |
| Manual logging | Structured logging |

## Weight and Image Processing Migration

The new modular system includes specialized actions for handling weight parsing and image processing. These actions provide consistent data normalization and quality improvements.

### Weight Field Migration

**Legacy Weight Handling:**
```python
# Manual weight extraction and parsing
try:
    weight_element = WebDriverWait(driver, 3).until(
        EC.presence_of_element_located(
            (By.XPATH, "//table[contains(@class, 'table')]//tr[td/strong[text()='Weight']]/td[2]")
        )
    )
    weight_html = weight_element.get_attribute("innerHTML")
    if weight_html:
        match = re.search(r"(\d*\.?\d+)\s*(lbs?|kg|oz)?", weight_html, re.IGNORECASE)
        if match:
            product_info["Weight"] = f"{match.group(1)} {match.group(2) or ''}".strip()
        else:
            product_info["Weight"] = ""
    else:
        product_info["Weight"] = ""
except (TimeoutException, NoSuchElementException):
    product_info["Weight"] = ""
```

**New Modular Weight Handling:**
```yaml
selectors:
  - name: "weight_raw"
    selector: "//table[contains(@class, 'table')]//tr[td/strong[text()='Weight']]/td[2]"
    attribute: "text"

workflows:
  - action: "extract"
    params:
      fields: ["weight_raw"]
  - action: "parse_weight"
    params:
      field: "weight_raw"
      target_unit: "lb"  # Options: lb, kg, oz, g
```

### Image Processing Migration

**Legacy Image Handling:**
```python
# Manual image collection and processing
try:
    image_urls = set()

    # Desktop thumbnails
    try:
        desktop_thumbs = WebDriverWait(driver, 3).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "#main-slider-desktop a[href*='/ccstore/v1/images']")
        )
        for el in desktop_thumbs:
            href = el.get_attribute("href")
            if href:
                if href.startswith("/ccstore"):
                    href = "https://www.bradleycaldwell.com" + href
                image_urls.add(href)
    except (TimeoutException, NoSuchElementException):
        pass

    # Mobile thumbnails
    try:
        mobile_thumbs = WebDriverWait(driver, 3).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "#main-slider-mobile a[href*='/ccstore/v1/images']")
        )
        for el in mobile_thumbs:
            href = el.get_attribute("href")
            if href:
                if href.startswith("/ccstore"):
                    href = "https://www.bradleycaldwell.com" + href
                image_urls.add(href)
    except (TimeoutException, NoSuchElementException):
        pass

    product_info["Image URLs"] = list(image_urls)
except Exception as e:
    product_info["Image URLs"] = []
```

**New Modular Image Handling:**
```yaml
selectors:
  - name: "images_raw"
    selector: "#main-slider-desktop a[href*='/ccstore/v1/images'], #main-slider-mobile a[href*='/ccstore/v1/images']"
    attribute: "href"
    multiple: true

workflows:
  - action: "extract"
    params:
      fields: ["images_raw"]
  - action: "process_images"
    params:
      field: "images_raw"
      quality_patterns:
        - regex: "^/ccstore"
          replacement: "https://www.bradleycaldwell.com/ccstore"
      filters:
        - type: "exclude_text"
          text: "placeholder"
        - type: "require_text"
          text: "/images"
      deduplicate: true
```

### Advanced Image Processing Examples

**Quality Upgrade Patterns:**
```yaml
- action: "process_images"
  params:
    field: "images"
    quality_patterns:
      - regex: "_small\\.jpg$"
        replacement: "_large.jpg"
      - regex: "\\?size=\\d+"
        replacement: "?size=1000"
      - regex: "/thumbs/"
        replacement: "/full/"
```

**Filtering Options:**
```yaml
- action: "process_images"
  params:
    field: "images"
    filters:
      - type: "exclude_text"
        text: "watermark"
      - type: "exclude_text"
        text: "placeholder"
      - type: "require_text"
        text: ".jpg"
      - type: "require_text"
        text: "product"
```

## Before/After Code Examples

### Example 1: Simple Product Search

**Before (Legacy):**
```python
def search_product(driver, sku):
    search_url = f"https://www.example.com/search?q={sku}"
    driver.get(search_url)
    time.sleep(2)

    # Click first result
    try:
        first_result = driver.find_element(By.CSS_SELECTOR, ".product-link")
        first_result.click()
        time.sleep(1)
    except NoSuchElementException:
        return None

    # Extract data
    try:
        name = driver.find_element(By.ID, "product-name").text
        price = driver.find_element(By.CLASS_NAME, "price").text
        return {"name": name, "price": price}
    except NoSuchElementException:
        return None
```

**After (Modular):**
```yaml
name: "example_shop"
base_url: "https://www.example.com"
selectors:
  - name: "product_name"
    selector: "#product-name"
    attribute: "text"
  - name: "price"
    selector: ".price"
    attribute: "text"
workflows:
  - action: "navigate"
    params:
      url: "https://www.example.com/search?q={sku}"
  - action: "wait_for"
    params:
      selector: ".product-link"
      timeout: 10
  - action: "click"
    params:
      selector: ".product-link"
  - action: "wait_for"
    params:
      selector: "#product-name"
      timeout: 10
  - action: "extract"
    params:
      fields: ["product_name", "price"]
```

### Example 2: Login Workflow

**Before (Legacy):**
```python
def login_to_site(driver, username, password):
    driver.get("https://www.example.com/login")
    time.sleep(2)

    # Fill login form
    username_field = driver.find_element(By.ID, "username")
    username_field.clear()
    username_field.send_keys(username)

    password_field = driver.find_element(By.ID, "password")
    password_field.clear()
    password_field.send_keys(password)

    # Submit form
    submit_button = driver.find_element(By.ID, "login-btn")
    submit_button.click()
    time.sleep(3)

    # Check if login successful
    try:
        driver.find_element(By.CLASS_NAME, "dashboard")
        return True
    except NoSuchElementException:
        return False
```

**After (Modular):**
```yaml
name: "example_with_login"
base_url: "https://www.example.com"
login:
  url: "https://www.example.com/login"
  username_field: "#username"
  password_field: "#password"
  submit_button: "#login-btn"
  success_indicator: ".dashboard"
selectors:
  - name: "product_name"
    selector: ".product-title"
    attribute: "text"
workflows:
  - action: "login"
    params:
      username: "{username}"
      password: "{password}"
  - action: "navigate"
    params:
      url: "https://www.example.com/products"
  - action: "extract"
    params:
      fields: ["product_name"]
```

### Example 3: Bradley Caldwell Scraper Migration

**Before (Legacy Bradley Scraper):**
```python
def scrape_single_product(SKU, driver, log_callback=None):
   search_url = f"https://www.bradleycaldwell.com/searchresults?Ntk=All|product.active%7C&Ntt=*{SKU}*&Nty=1&No=0&Nrpp=12&Rdm=323&searchType=simple&type=search"
   product_info = {"SKU": SKU}

   try:
       driver.get(search_url)

       # Wait for product or no results
       WebDriverWait(driver, 20).until(
           EC.any_of(
               EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-name")),
               EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'No products were found.')]"))
           )
       )

       # Check for no results
       try:
           not_found = driver.find_element(By.XPATH, "//h2[contains(text(), 'No products were found.')]")
           if not_found:
               return None
       except NoSuchElementException:
           pass

       # Extract name
       try:
           name_element = wait_for_element(driver, By.CSS_SELECTOR, "h1.product-name")
           time.sleep(2)
           product_info["Name"] = clean_string(name_element.text)
       except TimeoutException:
           product_info["Name"] = ""

       # Extract brand (multiple fallback selectors)
       brand_found = False
       brand_selectors = [
           "//div[@class='product-brand']/a",
           "//div[contains(@class, 'product-brand')]//a",
           "//span[@class='product-brand']",
           "//div[@class='product-brand']",
           "//a[contains(@href, '/brand/')]",
       ]

       for selector in brand_selectors:
           try:
               brand_element = WebDriverWait(driver, 3).until(
                   EC.presence_of_element_located((By.XPATH, selector))
               )
               brand_name = clean_string(brand_element.text)
               if brand_name and len(brand_name.strip()) > 0:
                   product_info["Brand"] = brand_name
                   brand_found = True
                   break
           except (TimeoutException, NoSuchElementException):
               continue

       # Extract weight
       try:
           weight_element = WebDriverWait(driver, 3).until(
               EC.presence_of_element_located((
                   By.XPATH, "//table[contains(@class, 'table')]//tr[td/strong[text()='Weight']]/td[2]"
               ))
           )
           weight_html = weight_element.get_attribute("innerHTML")
           if weight_html:
               match = re.search(r"(\d*\.?\d+)\s*(lbs?|kg|oz)?", weight_html, re.IGNORECASE)
               if match:
                   product_info["Weight"] = f"{match.group(1)} {match.group(2) or ''}".strip()
               else:
                   product_info["Weight"] = ""
       except (TimeoutException, NoSuchElementException):
           product_info["Weight"] = ""

       # Extract images (desktop and mobile carousels)
       try:
           image_urls = set()

           # Desktop thumbnails
           try:
               desktop_thumbs = WebDriverWait(driver, 3).until(
                   lambda d: d.find_elements(By.CSS_SELECTOR, "#main-slider-desktop a[href*='/ccstore/v1/images']")
               )
               for el in desktop_thumbs:
                   href = el.get_attribute("href")
                   if href:
                       if href.startswith("/ccstore"):
                           href = "https://www.bradleycaldwell.com" + href
                       image_urls.add(href)
           except (TimeoutException, NoSuchElementException):
               pass

           # Mobile thumbnails
           try:
               mobile_thumbs = WebDriverWait(driver, 3).until(
                   lambda d: d.find_elements(By.CSS_SELECTOR, "#main-slider-mobile a[href*='/ccstore/v1/images']")
               )
               for el in mobile_thumbs:
                   href = el.get_attribute("href")
                   if href:
                       if href.startswith("/ccstore"):
                           href = "https://www.bradleycaldwell.com" + href
                       image_urls.add(href)
           except (TimeoutException, NoSuchElementException):
               pass

           product_info["Image URLs"] = list(image_urls)
       except Exception as e:
           product_info["Image URLs"] = []

   except Exception as e:
       return None

   return product_info
```

**After (Modular Bradley Configuration):**
```yaml
name: "bradley"
base_url: "https://www.bradleycaldwell.com"
test_skus: ["035585499741"]
timeout: 30
retries: 3

selectors:
 - name: "Name"
   selector: "h1"
   attribute: "text"
 - name: "Brand"
   selector: "p a[href*='kong']"
   attribute: "text"
 - name: "Weight"
   selector: "//li[contains(text(), 'Weight:')]"
   attribute: "text"
 - name: "Images"
   selector: ".flex.max-w-full.shrink-0.flex-row.gap-2.overflow-x-auto.p-1 img"
   attribute: "src"
   multiple: true

workflows:
 - action: "navigate"
   params:
     url: "https://www.bradleycaldwell.com/search?term={sku}"

 - action: "wait_for"
   params:
     selector:
       [
         "//h1[contains(text(), 'Search results for')]",
         "//h3[contains(text(), 'Sorry, no results for')]",
       ]
     timeout: 20

 - action: "check_no_results"
   params:
     min_confidence: 0.8

 - action: "conditional_skip"
   params:
     if_flag: "no_results_found"

 - action: "click"
   params:
     selector: "article a"
     index: 0
     wait_after: 3

 - action: "wait_for"
   params:
     selector: "h1"
     timeout: 20

 - action: "wait"
   params:
     seconds: 2

 # Extract product details
 - action: "extract"
   params:
     fields: ["Name", "Brand", "Weight", "Images"]

 # Process weight data
 - action: "parse_weight"
   params:
     field: "Weight"
     target_unit: "lb"

 # Process and filter images
 - action: "process_images"
   params:
     field: "Images"
     quality_patterns:
       - regex: "^/ccstore"
         replacement: "https://www.bradleycaldwell.com/ccstore"
     filters:
       - type: "exclude_text"
         text: "placeholder"
       - type: "require_text"
         text: "/images"
     deduplicate: true

validation:
 no_results_selectors:
   - "//*[contains(text(), '0 items')]"
 no_results_text_patterns:
   - "0 items"

anti_detection:
 enable_captcha_detection: false
 enable_rate_limiting: false
 enable_human_simulation: true
 enable_session_rotation: false
 enable_blocking_handling: false
 max_retries_on_detection: 3
```

**Migration Benefits:**
- **Reduced Code Complexity**: From ~300 lines of complex Python logic to ~80 lines of declarative YAML
- **Built-in Error Handling**: Automatic retries, timeouts, and validation
- **Consistent Data Processing**: Standardized weight parsing and image processing
- **Easier Maintenance**: Changes to scraping logic don't require Python code modifications
- **Better Anti-Detection**: Integrated anti-detection capabilities
- **Improved Reliability**: Structured workflows with proper wait conditions and validation

## Troubleshooting Common Issues

### Issue: Selector Not Found
**Problem:** Elements not found during extraction
**Solution:** Update CSS selectors in YAML configuration

### Issue: Timeout Errors
**Problem:** Page loads taking too long
**Solution:** Adjust timeout values in configuration or add wait conditions

### Issue: Anti-Detection Triggers
**Problem:** CAPTCHA or blocking pages encountered
**Solution:** Enable and configure anti-detection modules

### Issue: Data Extraction Inconsistent
**Problem:** Different page layouts or dynamic content
**Solution:** Add multiple selectors with fallbacks or use more specific selectors

### Issue: Session Management
**Problem:** Login sessions not persisting
**Solution:** Configure session rotation and cookie handling

## Testing Migration

1. **Unit Test Configuration**: Validate YAML parsing
2. **Integration Test**: Test workflow execution with sample data
3. **Regression Test**: Compare results with legacy scraper
4. **Performance Test**: Measure execution time improvements

## Rollback Plan

If issues arise during migration:

1. Keep legacy scrapers in `src/scrapers_archive/`
2. Use feature flags to switch between systems
3. Gradually migrate scrapers one by one
4. Maintain both systems during transition period

## Best Practices

- **Start Small**: Migrate one scraper at a time
- **Test Thoroughly**: Validate data accuracy and completeness
- **Monitor Performance**: Track execution times and success rates
- **Document Changes**: Update any hardcoded references
- **Version Control**: Commit migration changes incrementally