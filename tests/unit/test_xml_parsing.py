import unittest
import os
import sys
import pandas as pd

# Add the inventory directory to the path so we can import the parsing function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'inventory'))

from process_xml_to_db import parse_xml_file_to_dataframe

class TestXMLParsing(unittest.TestCase):
    """Test cases for parsing ShopSite XML files."""

    def setUp(self):
        """Set up test fixtures."""
        # Path to the test XML file
        self.test_xml_path = os.path.join(os.path.dirname(__file__), '..', 'inventory', 'data', 'shopsite_test.xml')
        self.assertTrue(os.path.exists(self.test_xml_path), f"Test XML file not found: {self.test_xml_path}")

    def test_parse_single_product_xml(self):
        """Test parsing the single product test XML file."""
        # Parse the XML file
        df = parse_xml_file_to_dataframe(self.test_xml_path)

        # Print the parsed data for inspection
        print("\n📊 Parsed Product Data:")
        print("=" * 50)
        for col in df.columns:
            value = df.iloc[0][col]
            if len(str(value)) > 100:  # Truncate long values
                value = str(value)[:100] + "..."
            print(f"{col}: {value}")
        print("=" * 50)

        # Verify we got a DataFrame
        self.assertIsNotNone(df, "Parsing returned None")
        self.assertIsInstance(df, pd.DataFrame, "Result is not a DataFrame")

        # Should have exactly one product
        self.assertEqual(len(df), 1, f"Expected 1 product, got {len(df)}")

        # Get the first (and only) product
        product = df.iloc[0]

        # Test basic fields
        self.assertEqual(product['SKU'], '035585499741', "SKU mismatch")
        self.assertEqual(product['Name'], 'KONG Pull A Partz Pals Dog Toy Koala SM', "Name mismatch")
        self.assertEqual(product['Price'], '11.99', "Price mismatch")
        self.assertEqual(product['Weight'], '0.22', "Weight mismatch")
        self.assertEqual(product['ProductType'], 'Tangible', "ProductType mismatch")

        # Test ProductOnPages (special handling)
        self.assertEqual(product['ProductOnPages'], 'Dog Toys', "ProductOnPages mismatch")

        # Test ProductField values
        self.assertEqual(product['ProductField1'], 'instock041825', "ProductField1 mismatch")
        self.assertEqual(product['ProductField16'], 'KONG', "ProductField16 (Brand) mismatch")
        self.assertEqual(product['ProductField17'], 'dog', "ProductField17 mismatch")
        self.assertEqual(product['ProductField24'], 'dog supplies', "ProductField24 (Category) mismatch")
        self.assertEqual(product['ProductField25'], 'toys', "ProductField25 (Product Type) mismatch")
        self.assertEqual(product['ProductField32'], '850045168018|850007047436|835953000117|840139132117', "ProductField32 mismatch")

        # Test that empty fields are handled correctly
        self.assertEqual(product['SaleAmount'], '', "SaleAmount should be empty")
        self.assertEqual(product['Brand'], '', "Brand should be empty")

        # Test nested XML serialization (QuantityPricing should be serialized)
        self.assertIn('<QuantityPricing>', product['QuantityPricing'], "QuantityPricing not serialized as XML")
        self.assertIn('<Enabled>uncheck</Enabled>', product['QuantityPricing'], "QuantityPricing content missing")

        # Test that all expected fields are present
        expected_fields = [
            'SKU', 'Name', 'Price', 'Weight', 'ProductType', 'ProductOnPages',
            'ProductField1', 'ProductField16', 'ProductField17', 'ProductField24',
            'ProductField25', 'ProductField32', 'QuantityPricing', 'Graphic',
            'ProductDescription', 'ProductID', 'ProductGUID'
        ]

        for field in expected_fields:
            self.assertIn(field, product.index, f"Missing expected field: {field}")

        print("✅ All parsing tests passed!")

if __name__ == '__main__':
    unittest.main()