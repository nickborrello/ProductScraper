import sys
import os

# Add project root to the Python path to allow imports from src
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.classification.manager import classify_products_batch
from src.core.classification.ui import edit_classification_in_batch


def run_full_classification_test():
    """
    Performs a full, end-to-end test of the product classification system.
    1. Starts with a batch of unclassified products.
    2. Runs automatic classification using a specified method (e.g., 'local_llm').
    3. Opens the results in the interactive UI for review and finalization.
    4. Prints the final, user-approved results.
    """
    print("🚀 Starting Full End-to-End Classification Test...")
    print("=" * 50)

    # 1. Define a batch of products to be classified.
    products_to_classify = [
        {
            "Name": "Purina Pro Plan Adult Dog Food Chicken & Rice Formula",
            "Brand": "Purina",
            "SKU": "E2E_TEST_001",
        },
        {
            "Name": "Royal Canin Indoor Adult Cat Food Hairball Care",
            "Brand": "Royal Canin",
            "SKU": "E2E_TEST_002",
        },
        {
            "Name": "Kaytee Forti-Diet Pro Health Cockatiel Food",
            "Brand": "Kaytee",
            "SKU": "E2E_TEST_003",
        },
        # This is a non-pet product to test the classifier's range
        {
            "Name": "Craftsman 16oz Claw Hammer",
            "Brand": "Craftsman",
            "SKU": "E2E_TEST_004",
        },
    ]
    print(f"📋 Step 1: Defined a batch of {len(products_to_classify)} products.")
    for p in products_to_classify:
        print(f"  - {p['Name']}")
    print("-" * 50)

    # 2. Run automatic batch classification.
    # We'll use 'local_llm' which requires Ollama to be running.
    # You can change this to 'llm' (requires OpenRouter API key) or 'mock'.
    classification_method = "llm"
    print(
        f"🤖 Step 2: Running automatic classification using the '{classification_method}' method..."
    )

    try:
        auto_classified_products = classify_products_batch(
            products_to_classify, method=classification_method
        )
        print("✅ Automatic classification successful.")
        print("--- Auto-classification Results ---")
        for p in auto_classified_products:
            print(f"  - {p['Name'][:40]:<40} -> Category: {p.get('Category', 'N/A')}")
        print("-" * 50)
    except Exception as e:
        print(f"❌ ERROR: Automatic classification failed: {e}")
        print(
            "Please ensure the selected classification method is configured correctly."
        )
        print("For 'local_llm', make sure Ollama is installed and running.")
        print("For 'llm', ensure your OpenRouter API key is in settings.json.")
        return

    # 3. Open the results in the UI for finalization.
    print("🖥️ Step 3: Opening the interactive UI for review and finalization...")
    print("Please review the classifications and click 'Finish' when done.")

    final_products = edit_classification_in_batch(auto_classified_products)

    if not final_products:
        print("\n🛑 Test cancelled by user in the UI.")
        return

    # 4. Print the final, user-approved results.
    print("\n🎉 Step 4: Test Complete! Final User-Approved Classifications:")
    print("=" * 50)
    for product in final_products:
        print(f"  SKU: {product.get('SKU', 'N/A')}")
        print(f"  Name: {product.get('Name', 'N/A')}")
        print(f"  Category: {product.get('Category', 'None')}")
        print(f"  Product Type: {product.get('Product Type', 'None')}")
        print(f"  Product On Pages: {product.get('Product On Pages', 'None')}")
        print("-" * 20)


if __name__ == "__main__":
    run_full_classification_test()
