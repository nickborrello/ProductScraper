"""
Local LLM-based product classifier using Ollama for running models locally without API keys.
"""

import json
import os
import time
from pathlib import Path
from typing import Any

import ollama

# Configuration
OLLAMA_MODEL = "llama2"  # Default fallback
MAX_TOKENS = 1000
TEMPERATURE = 0.1  # Low temperature for consistent classifications

# Import settings manager
try:
    from src.core.settings_manager import settings

    _settings_available = True
except ImportError:
    try:
        # Fallback for when run as standalone
        from ..settings_manager import settings

        _settings_available = True
    except ImportError:
        # Last resort - try to load from settings.json directly
        config_path = Path(__file__).parent.parent.parent.parent / "settings.json"
        if config_path.exists():
            with open(config_path) as f:
                _config = json.load(f)
                _ollama_model = _config.get("ollama_model", OLLAMA_MODEL)
        else:
            _ollama_model = OLLAMA_MODEL
        _settings_available = False


class LocalLLMProductClassifier:
    """Local LLM-based product classifier using Ollama for running models
    locally without API keys."""

    def __init__(
        self,
        model_name: str | None = None,
        cache_file: Path | None = None,
        product_taxonomy: dict[str, list[str]] | None = None,
        product_pages: list[str] | None = None,
    ):
        # Try to get model name from settings first, then parameter, then environment, then default
        if model_name is None:
            if _settings_available:
                model_name = settings.get("ollama_model", OLLAMA_MODEL)
            else:
                model_name = _ollama_model
            if not model_name:
                model_name = os.getenv("OLLAMA_MODEL", OLLAMA_MODEL)

        self.model_name = model_name or OLLAMA_MODEL
        self.conversation_history = []
        self.classification_cache = {}  # Cache for classifications
        self.cache_file = cache_file or Path.home() / ".cache" / "productscraper_ollama_cache.json"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_cache()

        # Use provided taxonomy or import from taxonomy manager
        if product_taxonomy is None:
            try:
                from .taxonomy_manager import get_product_taxonomy

                self.product_taxonomy = get_product_taxonomy()
            except ImportError:
                try:
                    from src.core.classification.taxonomy_manager import get_product_taxonomy

                    self.product_taxonomy = get_product_taxonomy()
                except ImportError:
                    # Fallback - use a basic taxonomy
                    self.product_taxonomy = {
                        "Dog Food": [
                            "Dry Dog Food",
                            "Wet Dog Food",
                            "Adult Dog Food",
                            "Puppy Food",
                        ],
                        "Cat Food": [
                            "Dry Cat Food",
                            "Wet Cat Food",
                            "Adult Cat Food",
                            "Kitten Food",
                        ],
                    }
        else:
            self.product_taxonomy = product_taxonomy

        if product_pages is None:
            try:
                from .manager import PRODUCT_PAGES

                self.product_pages = PRODUCT_PAGES
            except ImportError:
                try:
                    from src.core.classification.manager import PRODUCT_PAGES

                    self.product_pages = PRODUCT_PAGES
                except ImportError:
                    # Fallback - use basic pages
                    self.product_pages = [
                        "Dog Food",
                        "Cat Food",
                        "Bird Supplies",
                        "All Pets",
                    ]
        else:
            self.product_pages = product_pages

        self._initialize_conversation()

        # Test Ollama connection
        try:
            ollama.list()
            print(f"✅ Ollama connection successful, using model: {self.model_name}")
        except Exception as e:
            raise ValueError(
                f"Ollama not available. Please install Ollama and ensure it's running: {e}"
            )

    def _initialize_conversation(self):
        """Initialize conversation with taxonomy and instructions."""
        try:
            from src.core.classification.manager import (
                UNIFIED_SINGLE_PRODUCT_JSON_FORMAT,
                UNIFIED_SYSTEM_PROMPT,
            )
        except ImportError:
            from .manager import UNIFIED_SINGLE_PRODUCT_JSON_FORMAT, UNIFIED_SYSTEM_PROMPT

        # Create comprehensive system prompt
        taxonomy_text = "PRODUCT TAXONOMY:\n"
        for category, product_types in self.product_taxonomy.items():
            taxonomy_text += f"\n{category}:\n"
            for pt in product_types:
                taxonomy_text += f"  - {pt}\n"

        pages_text = "COMMON PRODUCT PAGES:\n" + "\n".join(
            f"  - {page}" for page in self.product_pages
        )

        system_prompt = (
            UNIFIED_SYSTEM_PROMPT.format(taxonomy_text=taxonomy_text, pages_text=pages_text)
            + UNIFIED_SINGLE_PRODUCT_JSON_FORMAT
        )

        self.conversation_history = [{"role": "system", "content": system_prompt}]

    def _call_ollama(self, messages: list[dict], max_retries: int = 3) -> str | None:
        """Call Ollama API with retry logic."""
        for attempt in range(max_retries):
            try:
                response = ollama.chat(
                    model=self.model_name,
                    messages=messages,
                    options={
                        "temperature": TEMPERATURE,
                        "num_predict": MAX_TOKENS,
                    },
                )
                return response["message"]["content"]
            except Exception as e:
                print(f"Ollama API call failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff

        return None

    def classify_product(self, product_name: str, product_brand: str = "") -> dict[str, str]:
        """
        Classify a single product using local LLM with caching.

        Args:
            product_name: Product name
            product_brand: Product brand (optional)

        Returns:
            Dict with category, product_type, product_on_pages
        """
        # Check cache first
        cache_key = self._get_cache_key(product_name, product_brand)
        if cache_key in self.classification_cache:
            cached_result = self.classification_cache[cache_key]
            # Only use cache if it has actual classification data
            if any(cached_result.values()):
                print(f"📋 Using cached classification for: {product_name[:40]}...")
                return cached_result.copy()
            else:
                # Cached result is empty, remove it and re-classify
                del self.classification_cache[cache_key]
                self._save_cache()

        # Create user prompt
        user_prompt = "Classify this product:\n"
        if product_brand:
            user_prompt += f"Brand: {product_brand}\n"
        user_prompt += f"Name: {product_name}"

        # Add to conversation
        self.conversation_history.append({"role": "user", "content": user_prompt})

        # Call Ollama
        response = self._call_ollama(self.conversation_history)

        if not response:
            return {"category": "", "product_type": "", "product_on_pages": ""}

        # Add assistant response to conversation
        self.conversation_history.append({"role": "assistant", "content": response})

        # Parse JSON response
        result = self._parse_classification_response(response)

        # Only cache if result has actual data
        if any(result.values()):
            self.classification_cache[cache_key] = result.copy()
            self._save_cache()

        return result

    def classify_products_batch(
        self, products: list[dict[str, str]], batch_size: int = 15
    ) -> list[dict[str, str]]:
        """
        Classify multiple products in batch using efficient API calls.

        Args:
            products: List of product dicts with 'Name' and optional 'Brand'
            batch_size: Number of products per API call (default 15 for optimal token usage)

        Returns:
            List of classification results
        """
        print(f"🤖 Batch classifying {len(products)} products (batch size: {batch_size})...")

        # Filter out products without names
        valid_products = []
        valid_indices = []
        for i, product in enumerate(products):
            if product.get("Name", "").strip():
                valid_products.append(product)
                valid_indices.append(i)

        if not valid_products:
            return [{"category": "", "product_type": "", "product_on_pages": ""} for _ in products]

        # Use efficient batch processing
        valid_results = self.classify_products_batch_efficient(valid_products, batch_size)

        # Reconstruct full results list with empty results for invalid products
        results = [{"category": "", "product_type": "", "product_on_pages": ""} for _ in products]
        for idx, result in zip(valid_indices, valid_results, strict=False):
            results[idx] = result

        return results

    def classify_products_batch_efficient(
        self, products: list[dict[str, Any]], batch_size: int = 15
    ) -> list[dict[str, str]]:
        """
        Efficiently classify multiple products using batch API calls.

        Args:
            products: List of product dicts with essential fields (Name, Brand)
            batch_size: Number of products per API call (default 15 for optimal token usage)

        Returns:
            List of classification results
        """
        results = []

        # Process in batches
        for i in range(0, len(products), batch_size):
            batch = products[i : i + batch_size]
            batch_results = self._classify_batch_ollama_call(batch)
            results.extend(batch_results)

            # Progress indicator
            processed = min(i + batch_size, len(products))
            print(f"  📊 Classified {processed}/{len(products)} products")

        return results

    def _classify_batch_ollama_call(self, products: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Make a single API call for multiple products."""
        if not products:
            return []

        try:
            from src.core.classification.manager import UNIFIED_BATCH_JSON_FORMAT
        except ImportError:
            from .manager import UNIFIED_BATCH_JSON_FORMAT

        # Create batch prompt with essential product information
        batch_prompt = (
            "Classify these products. For each product, use the name and brand to "
            "determine the category and type.\n\n"
        )

        for i, product in enumerate(products, 1):
            batch_prompt += f"PRODUCT {i}:\n"

            # Include only essential fields for classification
            fields_to_include = [("Name", "Product Name"), ("Brand", "Brand")]

            for field_key, display_name in fields_to_include:
                value = product.get(field_key, "").strip()
                if value:
                    batch_prompt += f"  {display_name}: {value}\n"

            batch_prompt += "\n"

        batch_prompt += UNIFIED_BATCH_JSON_FORMAT

        # Construct messages for this specific call to keep it stateless and manage token usage
        messages_for_call = self.conversation_history[:1]  # Start with just the system prompt
        messages_for_call.append({"role": "user", "content": batch_prompt})

        # Call Ollama
        response = self._call_ollama(messages_for_call)

        if not response:
            # Return empty results for all products in batch
            return [{"category": "", "product_type": "", "product_on_pages": ""} for _ in products]

        # NOTE: We do not append the assistant response to the instance's conversation history
        # to keep each batch call stateless and prevent token usage from growing.

        # Parse batch JSON response
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)

                classifications = result.get("classifications", [])

                # Convert to expected format
                batch_results = []
                for i, product in enumerate(products):
                    # Find classification for this product index
                    product_classification = None
                    for cls in classifications:
                        if cls.get("product_index") == i + 1:
                            product_classification = cls
                            break

                    if product_classification:
                        batch_results.append(
                            {
                                "category": product_classification.get("category", ""),
                                "product_type": product_classification.get("product_type", ""),
                                "product_on_pages": product_classification.get(
                                    "product_on_pages", ""
                                ),
                            }
                        )
                    else:
                        batch_results.append(
                            {"category": "", "product_type": "", "product_on_pages": ""}
                        )

                return batch_results
            else:
                print(f"Could not parse batch JSON from response: {response[:200]}...")
                return [
                    {"category": "", "product_type": "", "product_on_pages": ""} for _ in products
                ]

        except json.JSONDecodeError as e:
            print(f"Batch JSON parsing error: {e}")
            print(f"Response: {response[:500]}...")
            return [{"category": "", "product_type": "", "product_on_pages": ""} for _ in products]

    def reset_conversation(self):
        """Reset conversation thread."""
        self._initialize_conversation()

    def _load_cache(self):
        """Load classification cache from disk."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file) as f:
                    self.classification_cache = json.load(f)
                print(f"📋 Loaded {len(self.classification_cache)} cached classifications")
        except Exception as e:
            print(f"⚠️ Could not load cache: {e}")
            self.classification_cache = {}

    def _save_cache(self):
        """Save classification cache to disk."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.classification_cache, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save cache: {e}")

    def _get_cache_key(self, product_name: str, product_brand: str = "") -> str:
        """Generate cache key for product."""
        return f"{product_brand}|{product_name}".strip("|")

    def classify_product_with_cache(
        self, product_name: str, product_brand: str = ""
    ) -> dict[str, str]:
        """
        Classify a product with caching.

        Args:
            product_name: Product name
            product_brand: Product brand (optional)

        Returns:
            Dict with category, product_type, product_on_pages
        """
        cache_key = f"{product_name}|{product_brand}".strip("|")

        # Check cache first
        if cache_key in self.classification_cache:
            print(f"✅ Cache hit for '{cache_key}'")
            return self.classification_cache[cache_key]

        # If not in cache, classify using LLM
        result = self.classify_product(product_name, product_brand)

        # Add to cache
        self.classification_cache[cache_key] = result
        self._save_cache()  # Save cache to file

        return result

    def _parse_classification_response(self, response: str) -> dict[str, str]:
        """Parse classification response from LLM."""
        try:
            # Extract JSON from response (LLM might add extra text)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)

                return {
                    "category": result.get("category", ""),
                    "product_type": result.get("product_type", ""),
                    "product_on_pages": result.get("product_on_pages", ""),
                }
            else:
                print(f"Could not parse JSON from response: {response}")
                return {"category": "", "product_type": "", "product_on_pages": ""}

        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response: {response}")
            return {"category": "", "product_type": "", "product_on_pages": ""}


# Global classifier instance
_local_llm_classifier = None


def get_local_llm_classifier(
    model_name: str | None = None,
    product_taxonomy: dict[str, list[str]] | None = None,
    product_pages: list[str] | None = None,
) -> LocalLLMProductClassifier:
    """Get or create local LLM classifier instance."""
    global _local_llm_classifier
    if _local_llm_classifier is None:
        try:
            _local_llm_classifier = LocalLLMProductClassifier(
                model_name,
                product_taxonomy=product_taxonomy,
                product_pages=product_pages,
            )
            print("✅ Local LLM classifier initialized")
        except ValueError as e:
            print(f"[ERROR] Local LLM classifier initialization failed: {e}")
            return None
    return _local_llm_classifier


def reset_local_llm_classifier():
    """Reset the global classifier instance and clear cache (for testing)."""
    global _local_llm_classifier
    if _local_llm_classifier:
        # Clear the cache file
        try:
            if _local_llm_classifier.cache_file.exists():
                _local_llm_classifier.cache_file.unlink()
        except Exception:
            pass  # Ignore errors when deleting cache file
    _local_llm_classifier = None


def classify_product_local_llm(
    product_info: dict[str, Any],
    product_taxonomy: dict[str, list[str]] | None = None,
    product_pages: list[str] | None = None,
) -> dict[str, str]:
    """
    Classify a product using local LLM via Ollama (no API key required).

    Args:
        product_info: Dict with product details (Name, Brand, Weight, Price, etc.)
        product_taxonomy: Product taxonomy dictionary (optional)
        product_pages: List of product pages (optional)

    Returns:
        Dict with category, product_type, product_on_pages
    """
    classifier = get_local_llm_classifier(
        product_taxonomy=product_taxonomy, product_pages=product_pages
    )
    if not classifier:
        return {"Category": "", "Product Type": "", "Product On Pages": ""}

    product_name = product_info.get("Name", "").strip()
    if not product_name:
        return {"Category": "", "Product Type": "", "Product On Pages": ""}

    # For now, still use simple classification (could be enhanced to use batch method)
    product_brand = product_info.get("Brand", "").strip()

    try:
        result = classifier.classify_product(product_name, product_brand)

        # Convert to the format expected by existing system
        return {
            "Category": result.get("category", ""),
            "Product Type": result.get("product_type", ""),
            "Product On Pages": result.get("product_on_pages", ""),
        }

    except Exception as e:
        print(f"⚠️ Local LLM classification failed: {e}")
        return {"Category": "", "Product Type": "", "Product On Pages": ""}


# Test the local LLM classifier
if __name__ == "__main__":
    import os
    import sys

    # Add project root to path to allow direct script execution
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from src.core.classification.local_llm_classifier import get_local_llm_classifier

    print("🧠 Testing Local LLM Product Classifier")
    print("=" * 50)

    # Test products - mix of pet and non-pet products
    test_products = [
        {
            "Name": "Purina Pro Plan Adult Dog Food Chicken & Rice Formula",
            "Brand": "Purina",
        },
        {
            "Name": "Royal Canin Indoor Adult Cat Food Hairball Care",
            "Brand": "Royal Canin",
        },
        {"Name": "Kaytee Forti-Diet Pro Health Cockatiel Food", "Brand": "Kaytee"},
        {"Name": "Stanley 24oz Stainless Steel Water Bottle", "Brand": "Stanley"},
        {"Name": "Craftsman 16oz Claw Hammer", "Brand": "Craftsman"},
        {"Name": " Scotts Turf Builder Lawn Fertilizer", "Brand": "Scotts"},
        {"Name": "Mobil 1 Synthetic Motor Oil 5W-30", "Brand": "Mobil 1"},
    ]

    classifier = get_local_llm_classifier()
    if classifier:
        print("🤖 Classifying test products...")
        results = classifier.classify_products_batch(test_products)

        for i, (product, result) in enumerate(zip(test_products, results, strict=False), 1):
            print(f"\n📦 Product {i}: {product['Name'][:50]}")
            print(f"   Category: {result.get('category', 'N/A')}")
            print(f"   Product Type: {result.get('product_type', 'N/A')}")
            print(f"   Product On Pages: {result.get('product_on_pages', 'N/A')}")

        print("\n✅ Local LLM classification test completed!")
    else:
        print("[ERROR] Could not initialize local LLM classifier - check Ollama installation")
