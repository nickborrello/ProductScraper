"""
LLM-Based Product Classification Module
Uses OpenAI GPT API for accurate product classification with persistent context.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # Try to load from config file
    config_path = Path(__file__).parent.parent.parent / "settings.json"
    if config_path.exists():
        with open(config_path, "r") as f:
            config = json.load(f)
            OPENAI_API_KEY = config.get("openai_api_key")

MODEL = "gpt-4o-mini"  # Cost-effective and capable
MAX_TOKENS = 1000
TEMPERATURE = 0.1  # Low temperature for consistent classifications

# Comprehensive product taxonomy - includes both pet and general products
GENERAL_PRODUCT_TAXONOMY = {
    # Pet Products
    "Dog Food": [
        "Dry Dog Food",
        "Wet Dog Food",
        "Raw Dog Food",
        "Freeze Dried Dog Food",
        "Puppy Food",
        "Adult Dog Food",
        "Senior Dog Food",
        "Grain Free Dog Food",
        "Limited Ingredient Dog Food",
        "Organic Dog Food",
        "Dog Treats",
        "Dog Biscuits",
        "Dog Dental Chews",
        "Dog Training Treats",
    ],
    "Cat Food": [
        "Dry Cat Food",
        "Wet Cat Food",
        "Raw Cat Food",
        "Freeze Dried Cat Food",
        "Kitten Food",
        "Adult Cat Food",
        "Senior Cat Food",
        "Hairball Cat Food",
        "Grain Free Cat Food",
        "Limited Ingredient Cat Food",
        "Organic Cat Food",
        "Cat Treats",
        "Cat Hairball Treats",
        "Cat Dental Treats",
    ],
    "Bird Supplies": [
        "Bird Food",
        "Bird Seed",
        "Bird Pellets",
        "Bird Treats",
        "Bird Cages",
        "Bird Toys",
        "Bird Perches",
        "Bird Healthcare",
        "Bird Vitamins",
        "Bird Supplements",
    ],
    "Fish Supplies": [
        "Fish Food",
        "Tropical Fish Flakes",
        "Goldfish Food",
        "Betta Food",
        "Fish Tanks",
        "Aquarium Filters",
        "Fish Water Treatments",
        "Fish Tank Decorations",
        "Fish Nets",
        "Fish Healthcare",
    ],
    "Small Pet Food": [
        "Rabbit Food",
        "Guinea Pig Food",
        "Hamster Food",
        "Gerbil Food",
        "Mouse Food",
        "Rat Food",
        "Ferret Food",
        "Chinchilla Food",
        "Small Pet Treats",
        "Small Pet Hay",
        "Small Pet Bedding",
    ],
    "Reptile Supplies": [
        "Reptile Food",
        "Bearded Dragon Food",
        "Leopard Gecko Food",
        "Snake Food",
        "Lizard Food",
        "Turtle Food",
        "Reptile Vitamins",
        "Reptile Heating",
        "Reptile Lighting",
        "Reptile Substrates",
        "Reptile Terrariums",
        "Reptile Healthcare",
    ],
    "Pet Toys": [
        "Dog Toys",
        "Cat Toys",
        "Bird Toys",
        "Small Pet Toys",
        "Chew Toys",
        "Plush Toys",
        "Interactive Toys",
        "Puzzle Toys",
    ],
    "Pet Healthcare": [
        "Dog Medications",
        "Cat Medications",
        "Bird Medications",
        "Joint Supplements",
        "Digestive Supplements",
        "Skin Care",
        "Flea & Tick",
        "Heartworm Prevention",
        "Dental Care",
    ],
    "Pet Grooming": [
        "Dog Shampoos",
        "Cat Shampoos",
        "Pet Brushes",
        "Pet Clippers",
        "Nail Clippers",
        "Ear Cleaners",
        "Pet Cologne",
    ],
    "Pet Beds & Carriers": [
        "Dog Beds",
        "Cat Beds",
        "Pet Carriers",
        "Pet Crates",
        "Pet Blankets",
        "Pet Pillows",
    ],
    "Pet Bowls & Feeders": [
        "Dog Bowls",
        "Cat Bowls",
        "Bird Bowls",
        "Automatic Feeders",
        "Pet Water Fountains",
        "Slow Feed Bowls",
    ],
    # Non-Pet Products
    "Hardware": [
        "Tools",
        "Fasteners",
        "Plumbing",
        "Electrical",
        "HVAC",
        "Paint",
        "Lumber",
        "Hardware Accessories",
        "Power Tools",
        "Hand Tools",
    ],
    "Lawn & Garden": [
        "Seeds",
        "Fertilizer",
        "Tools",
        "Plants",
        "Gardening Supplies",
        "Lawn Care",
        "Outdoor Furniture",
        "Grills",
        "Pest Control",
        "Irrigation",
    ],
    "Farm Supplies": [
        "Fencing",
        "Feeders",
        "Equipment",
        "Animal Health",
        "Farm Tools",
        "Livestock Supplies",
        "Poultry Supplies",
        "Barn Equipment",
        "Tractor Parts",
    ],
    "Home & Kitchen": [
        "Cleaning",
        "Storage",
        "Appliances",
        "Decor",
        "Kitchen Tools",
        "Bathroom Supplies",
        "Bedding",
        "Furniture",
        "Home Improvement",
        "Organization",
    ],
    "Automotive": [
        "Parts",
        "Tools",
        "Maintenance",
        "Accessories",
        "Tires",
        "Batteries",
        "Oil",
        "Filters",
        "Brakes",
        "Engine Parts",
    ],
    "Farm Animal Supplies": [
        "Chicken Feed",
        "Goat Feed",
        "Sheep Feed",
        "Pig Feed",
        "Livestock Medications",
        "Animal Supplements",
        "Farm Equipment",
    ],
}

# Common product pages - includes both pet and general products
PRODUCT_PAGES = [
    # Pet Pages
    "Dog Food Shop All",
    "Cat Food Shop All",
    "Bird Supplies Shop All",
    "Fish Supplies Shop All",
    "Small Pet Supplies Shop All",
    "Reptile Supplies Shop All",
    "Pet Toys Shop All",
    "Pet Healthcare Shop All",
    "Pet Grooming Shop All",
    "Dog Supplies Shop All",
    "Cat Supplies Shop All",
    "Pet Beds Shop All",
    # General Pages
    "Hardware Shop All",
    "Lawn & Garden Shop All",
    "Farm Supplies Shop All",
    "Home & Kitchen Shop All",
    "Automotive Shop All",
    "Farm Animal Supplies Shop All",
    # Common Pages
    "Brand Pages",
    "Sale Items",
    "New Arrivals",
    "Best Sellers",
]


class LLMProductClassifier:
    """LLM-based product classifier using OpenAI API with conversation threads."""

    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable or add to settings.json"
            )

        self.api_key = OPENAI_API_KEY
        self.conversation_history = []
        self.classification_cache = {}  # Cache for classifications
        self.cache_file = Path.home() / ".cache" / "productscraper_llm_cache.json"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_cache()
        self._initialize_conversation()

    def _initialize_conversation(self):
        """Initialize conversation with taxonomy and instructions."""

        # Create comprehensive system prompt
        taxonomy_text = "PRODUCT TAXONOMY:\n"
        for category, product_types in GENERAL_PRODUCT_TAXONOMY.items():
            taxonomy_text += f"\n{category.upper()}:\n"
            for pt in product_types:
                taxonomy_text += f"  - {pt}\n"

        pages_text = "COMMON PRODUCT PAGES:\n" + "\n".join(
            f"  - {page}" for page in PRODUCT_PAGES
        )

        system_prompt = f"""You are an expert e-commerce product classifier for a retail store.

{taxonomy_text}

{pages_text}

CLASSIFICATION RULES:
1. Always choose from the provided taxonomy - do not create new categories or product types
2. For Category: Choose the most specific main category that fits
3. For Product Type: Choose 1-3 most relevant product types from that category
4. For Product On Pages: Choose 2-4 most relevant pages where this product should appear
5. Consider the product purpose and target market
6. If uncertain, choose the closest match from the taxonomy

Return classifications in this exact JSON format:
{{
    "category": "Main Category Name",
    "product_type": "Product Type 1|Product Type 2",
    "product_on_pages": "Page 1|Page 2|Page 3"
}}

Be consistent and accurate in your classifications."""

        self.conversation_history = [{"role": "system", "content": system_prompt}]

    def _call_openai(self, messages: List[Dict], max_retries: int = 3) -> Optional[str]:
        """Call OpenAI API with retry logic."""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": MODEL,
                        "messages": messages,
                        "max_tokens": MAX_TOKENS,
                        "temperature": TEMPERATURE,
                    },
                    timeout=30,
                )

                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    print(
                        f"OpenAI API error (attempt {attempt + 1}): {response.status_code} - {response.text}"
                    )

            except Exception as e:
                print(f"OpenAI API call failed (attempt {attempt + 1}): {e}")

            if attempt < max_retries - 1:
                time.sleep(2**attempt)  # Exponential backoff

        return None

    def classify_product(
        self, product_name: str, product_brand: str = ""
    ) -> Dict[str, str]:
        """
        Classify a single product using LLM with caching.

        Args:
            product_name: Product name
            product_brand: Product brand (optional)

        Returns:
            Dict with category, product_type, product_on_pages
        """
        # Check cache first
        cache_key = self._get_cache_key(product_name, product_brand)
        if cache_key in self.classification_cache:
            print(f"📋 Using cached classification for: {product_name[:40]}...")
            return self.classification_cache[cache_key].copy()

        # Create user prompt
        user_prompt = f"Classify this pet product:\n"
        if product_brand:
            user_prompt += f"Brand: {product_brand}\n"
        user_prompt += f"Name: {product_name}"

        # Add to conversation
        self.conversation_history.append({"role": "user", "content": user_prompt})

        # Call API
        response = self._call_openai(self.conversation_history)

        if not response:
            return {"category": "", "product_type": "", "product_on_pages": ""}

        # Add assistant response to conversation
        self.conversation_history.append({"role": "assistant", "content": response})

        # Parse JSON response
        result = self._parse_classification_response(response)

        # Cache the result
        self.classification_cache[cache_key] = result.copy()
        self._save_cache()

        return result

    def classify_products_batch(
        self, products: List[Dict[str, str]], batch_size: int = 5
    ) -> List[Dict[str, str]]:
        """
        Classify multiple products in batch using efficient API calls.

        Args:
            products: List of product dicts with 'Name' and optional 'Brand'
            batch_size: Number of products per API call (default 5 for optimal token usage)

        Returns:
            List of classification results
        """
        print(
            f"🤖 Batch classifying {len(products)} products (batch size: {batch_size})..."
        )

        # Filter out products without names
        valid_products = []
        valid_indices = []
        for i, product in enumerate(products):
            if product.get("Name", "").strip():
                valid_products.append(product)
                valid_indices.append(i)

        if not valid_products:
            return [
                {"category": "", "product_type": "", "product_on_pages": ""}
                for _ in products
            ]

        # Use efficient batch processing
        valid_results = self.classify_products_batch_efficient(
            valid_products, batch_size
        )

        # Reconstruct full results list with empty results for invalid products
        results = [
            {"category": "", "product_type": "", "product_on_pages": ""}
            for _ in products
        ]
        for idx, result in zip(valid_indices, valid_results):
            results[idx] = result

        return results

    def classify_products_batch_efficient(
        self, products: List[Dict[str, Any]], batch_size: int = 5
    ) -> List[Dict[str, str]]:
        """
        Efficiently classify multiple products using batch API calls.

        Args:
            products: List of product dicts with essential fields (Name, Brand)
            batch_size: Number of products per API call (default 5 for optimal token usage)

        Returns:
            List of classification results
        """
        results = []

        # Process in batches
        for i in range(0, len(products), batch_size):
            batch = products[i : i + batch_size]
            batch_results = self._classify_batch_api_call(batch)
            results.extend(batch_results)

            # Progress indicator
            processed = min(i + batch_size, len(products))
            print(f"  📊 Classified {processed}/{len(products)} products")

        return results

    def _classify_batch_api_call(
        self, products: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Make a single API call for multiple products."""
        if not products:
            return []

        # Create batch prompt with essential product information
        batch_prompt = "Classify these products. For each product, use the name and brand to determine the category and type.\n\n"

        for i, product in enumerate(products, 1):
            batch_prompt += f"PRODUCT {i}:\n"

            # Include only essential fields for classification
            fields_to_include = [("Name", "Product Name"), ("Brand", "Brand")]

            for field_key, display_name in fields_to_include:
                value = product.get(field_key, "").strip()
                if value:
                    batch_prompt += f"  {display_name}: {value}\n"

            batch_prompt += "\n"

        batch_prompt += "Return classifications in this exact JSON format:\n"
        batch_prompt += """{
  "classifications": [
    {
      "product_index": 1,
      "category": "Main Category",
      "product_type": "Type 1|Type 2",
      "product_on_pages": "Page 1|Page 2|Page 3",
      "confidence": "high|medium|low",
      "reasoning": "Brief explanation"
    },
    ...
  ]
}"""

        # Add to conversation
        self.conversation_history.append({"role": "user", "content": batch_prompt})

        # Call API
        response = self._call_openai(self.conversation_history)

        if not response:
            # Return empty results for all products in batch
            return [
                {"category": "", "product_type": "", "product_on_pages": ""}
                for _ in products
            ]

        # Add assistant response to conversation
        self.conversation_history.append({"role": "assistant", "content": response})

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
                                "product_type": product_classification.get(
                                    "product_type", ""
                                ),
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
                    {"category": "", "product_type": "", "product_on_pages": ""}
                    for _ in products
                ]

        except json.JSONDecodeError as e:
            print(f"Batch JSON parsing error: {e}")
            print(f"Response: {response[:500]}...")
            return [
                {"category": "", "product_type": "", "product_on_pages": ""}
                for _ in products
            ]

    def reset_conversation(self):
        """Reset conversation thread."""
        self._initialize_conversation()

    def _load_cache(self):
        """Load classification cache from disk."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r") as f:
                    self.classification_cache = json.load(f)
                print(
                    f"📋 Loaded {len(self.classification_cache)} cached classifications"
                )
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
    ) -> Dict[str, str]:
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

    def _parse_classification_response(self, response: str) -> Dict[str, str]:
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
_llm_classifier = None


def get_llm_classifier() -> LLMProductClassifier:
    """Get or create LLM classifier instance."""
    global _llm_classifier
    if _llm_classifier is None:
        try:
            _llm_classifier = LLMProductClassifier()
            print("✅ LLM classifier initialized")
        except ValueError as e:
            print(f"❌ LLM classifier initialization failed: {e}")
            return None
    return _llm_classifier


def classify_product_llm(product_info: Dict[str, Any]) -> Dict[str, str]:
    """
    Classify a product using LLM API with rich context.

    Args:
        product_info: Dict with product details (Name, Brand, Weight, Price, etc.)

    Returns:
        Dict with category, product_type, product_on_pages
    """
    classifier = get_llm_classifier()
    if not classifier:
        return {"category": "", "product_type": "", "product_on_pages": ""}

    product_name = product_info.get("Name", "").strip()
    if not product_name:
        return {"category": "", "product_type": "", "product_on_pages": ""}

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
        print(f"⚠️ LLM classification failed: {e}")
        return {"Category": "", "Product Type": "", "Product On Pages": ""}


# Test the LLM classifier
if __name__ == "__main__":
    print("🧠 Testing LLM Product Classifier")
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

    classifier = get_llm_classifier()
    if classifier:
        print("🤖 Classifying test products...")
        results = classifier.classify_products_batch(test_products)

        for i, (product, result) in enumerate(zip(test_products, results), 1):
            print(f"\n📦 Product {i}: {product['Name'][:50]}")
            print(f"   Category: {result.get('category', 'N/A')}")
            print(f"   Product Type: {result.get('product_type', 'N/A')}")
            print(f"   Product On Pages: {result.get('product_on_pages', 'N/A')}")

        print("\n✅ LLM classification test completed!")
    else:
        print("❌ Could not initialize LLM classifier - check API key")
