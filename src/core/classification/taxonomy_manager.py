"""
Taxonomy Management System
Handles loading, updating, and refreshing product taxonomy from database.
"""

import json
import sqlite3
from pathlib import Path
from typing import cast


class TaxonomyManager:
    """Manages product taxonomy with database integration"""

    def __init__(self, taxonomy_file: str | None = None, db_path: str | None = None):
        """
        Initialize taxonomy manager

        Args:
            taxonomy_file: Path to JSON taxonomy file
            db_path: Path to SQLite database
        """
        if taxonomy_file is None:
            # Default: src/data/taxonomy.json relative to project root
            script_dir = Path(__file__).parent.parent.parent.parent
            self.taxonomy_file = script_dir / "src" / "data" / "taxonomy.json"
        else:
            self.taxonomy_file = Path(taxonomy_file)

        if db_path is None:
            # Default database path
            script_dir = Path(__file__).parent.parent.parent.parent
            self.db_path = script_dir / "src" / "data" / "databases" / "products.db"
        else:
            self.db_path = Path(db_path)

        self.taxonomy_file.parent.mkdir(parents=True, exist_ok=True)

    def load_taxonomy(self) -> dict[str, list[str]]:
        """
        Load taxonomy from JSON file, or create default if file doesn't exist

        Returns:
            Dictionary mapping categories to lists of product types
        """
        if self.taxonomy_file.exists():
            try:
                with open(self.taxonomy_file, encoding="utf-8") as f:
                    return cast(dict[str, list[str]], json.load(f))
            except (OSError, json.JSONDecodeError) as e:
                print(f"⚠️ Error loading taxonomy file: {e}")
                print("📝 Using default taxonomy...")

        # Return default taxonomy if file doesn't exist or is corrupted
        return self._get_default_taxonomy()

    def save_taxonomy(self, taxonomy: dict[str, list[str]]) -> None:
        """
        Save taxonomy to JSON file

        Args:
            taxonomy: Dictionary mapping categories to lists of product types
        """
        try:
            with open(self.taxonomy_file, "w", encoding="utf-8") as f:
                json.dump(taxonomy, f, indent=2, ensure_ascii=False)
            print(f"💾 Taxonomy saved to {self.taxonomy_file}")
        except OSError as e:
            print(f"❌ Error saving taxonomy: {e}")

    def refresh_from_database(self, save_changes: bool = True) -> dict[str, list[str]]:
        """
        Refresh taxonomy by scanning database for new categories and product types

        Args:
            save_changes: Whether to save updated taxonomy to file

        Returns:
            Updated taxonomy dictionary
        """
        print("🔄 Refreshing taxonomy from database...")

        # Get entries from database
        db_categories = self._get_distinct_categories_from_db()
        db_product_types = self._get_distinct_product_types_from_db()

        # Build taxonomy entirely from database
        updated_taxonomy: dict[str, list[str]] = {}
        for category in db_categories:
            updated_taxonomy[category] = []

        # Add product types to categories
        for category, types in db_product_types.items():
            if category in updated_taxonomy:
                updated_taxonomy[category] = sorted(types)

        # Save if requested
        if save_changes:
            self.save_taxonomy(updated_taxonomy)

        # Report changes
        old_taxonomy = self.load_taxonomy()
        self._report_changes(old_taxonomy, updated_taxonomy)

        return updated_taxonomy

    def _get_distinct_categories_from_db(self) -> set[str]:
        """Get distinct categories from database"""
        categories = set()

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Query distinct categories (exclude empty/null values)
            cursor.execute(
                """
                SELECT DISTINCT Category
                FROM products
                WHERE Category IS NOT NULL
                AND Category != ''
                AND TRIM(Category) != ''
            """
            )

            for row in cursor.fetchall():
                if row[0]:
                    # Split combined categories on "|" and add each individual category
                    combined_category = row[0].strip()
                    individual_categories = [
                        cat.strip() for cat in combined_category.split("|") if cat.strip()
                    ]
                    # Normalize each category name
                    normalized_categories = [
                        self._normalize_category_name(cat) for cat in individual_categories
                    ]
                    categories.update(normalized_categories)

            conn.close()

        except sqlite3.Error as e:
            print(f"❌ Database error getting categories: {e}")
        except FileNotFoundError:
            print(f"❌ Database not found: {self.db_path}")

        return categories

    def _get_distinct_product_types_from_db(self) -> dict[str, set[str]]:
        """
        Get distinct product types from database, grouped by category

        Returns:
            Dictionary mapping categories to sets of product types
        """
        product_types: dict[str, set[str]] = {}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Query product types with their categories
            cursor.execute(
                """
                SELECT Category, Product_Type
                FROM products
                WHERE Product_Type IS NOT NULL
                AND Product_Type != ''
                AND TRIM(Product_Type) != ''
            """
            )

            for row in cursor.fetchall():
                category = row[0].strip() if row[0] else ""
                product_type = row[1].strip() if row[1] else ""

                if category and product_type:
                    # Split combined categories on "|" and add product type to each individual category
                    individual_categories = [
                        cat.strip() for cat in category.split("|") if cat.strip()
                    ]

                    # Split combined product types on "|" and add each individual type
                    individual_product_types = [
                        self._normalize_category_name(pt.strip())
                        for pt in product_type.split("|")
                        if pt.strip()
                    ]

                    for individual_category in individual_categories:
                        normalized_category = self._normalize_category_name(individual_category)
                        if normalized_category not in product_types:
                            product_types[normalized_category] = set()
                        product_types[normalized_category].update(individual_product_types)

            conn.close()

        except sqlite3.Error as e:
            print(f"❌ Database error getting product types: {e}")
        except FileNotFoundError:
            print(f"❌ Database not found: {self.db_path}")

        return product_types

    def _merge_database_entries(
        self,
        current_taxonomy: dict[str, list[str]],
        db_categories: set[str],
        db_product_types: dict[str, set[str]],
    ) -> dict[str, list[str]]:
        """
        Merge database entries into current taxonomy

        Args:
            current_taxonomy: Current taxonomy dictionary
            db_categories: New categories from database
            db_product_types: New product types from database, grouped by category

        Returns:
            Updated taxonomy dictionary
        """
        updated_taxonomy = current_taxonomy.copy()

        # Add new categories
        for category in db_categories:
            if category not in updated_taxonomy:
                updated_taxonomy[category] = []
                print(f"➕ Added new category: {category}")

        # Add new product types to existing categories
        for category, types in db_product_types.items():
            if category not in updated_taxonomy:
                updated_taxonomy[category] = []

            current_types = set(updated_taxonomy[category])
            new_types = types - current_types

            if new_types:
                updated_taxonomy[category].extend(sorted(new_types))
                print(
                    f"➕ Added {len(new_types)} new product types to {category}: {sorted(new_types)}"
                )

        # Sort product types within each category
        for category in updated_taxonomy:
            updated_taxonomy[category] = sorted(updated_taxonomy[category])

        return updated_taxonomy

    def _report_changes(
        self, old_taxonomy: dict[str, list[str]], new_taxonomy: dict[str, list[str]]
    ) -> None:
        """Report taxonomy changes"""
        old_categories = set(old_taxonomy.keys())
        new_categories = set(new_taxonomy.keys())

        new_category_count = len(new_categories - old_categories)
        total_categories = len(new_categories)

        total_old_types = sum(len(types) for types in old_taxonomy.values())
        total_new_types = sum(len(types) for types in new_taxonomy.values())
        new_type_count = total_new_types - total_old_types

        print("📊 Taxonomy Update Summary:")
        print(f"   Categories: {total_categories} total ({new_category_count} new)")
        print(f"   Product Types: {total_new_types} total ({new_type_count} new)")

    def _normalize_category_name(self, category: str) -> str:
        """Normalize category name to proper title case"""
        if not category:
            return category

        # Convert to title case, but handle special cases
        normalized = category.strip().title()

        # Handle special cases that shouldn't be title cased
        special_cases = {
            "And": "and",
            "Or": "or",
            "Of": "of",
            "The": "the",
            "A": "a",
            "An": "an",
            "In": "in",
            "On": "on",
            "At": "at",
            "To": "to",
            "For": "for",
            "With": "with",
            "By": "by",
            "From": "from",
        }

        words = normalized.split()
        for i, word in enumerate(words):
            if word in special_cases and i > 0:  # Don't lowercase first word
                words[i] = special_cases[word]

        return " ".join(words)

    def _get_default_taxonomy(self) -> dict[str, list[str]]:
        """Get the default taxonomy (same as in manager.py)"""
        return {
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


# Global instance for easy access
_taxonomy_manager = None


def get_taxonomy_manager() -> TaxonomyManager:
    """Get global taxonomy manager instance"""
    global _taxonomy_manager
    if _taxonomy_manager is None:
        _taxonomy_manager = TaxonomyManager()
    return _taxonomy_manager


def get_product_taxonomy() -> dict[str, list[str]]:
    """Get current product taxonomy"""
    return get_taxonomy_manager().load_taxonomy()


def refresh_taxonomy_from_database(save_changes: bool = True) -> dict[str, list[str]]:
    """Refresh taxonomy from database and optionally save changes"""
    return get_taxonomy_manager().refresh_from_database(save_changes=save_changes)


# Test functions
if __name__ == "__main__":
    print("🧪 Testing Taxonomy Manager")
    print("=" * 50)

    # Initialize manager
    manager = TaxonomyManager()

    # Load current taxonomy
    print("📂 Loading taxonomy...")
    taxonomy = manager.load_taxonomy()
    print(f"📊 Loaded {len(taxonomy)} categories")

    # Refresh from database
    print("\n🔄 Refreshing from database...")
    updated_taxonomy = manager.refresh_from_database(save_changes=False)
    print(f"📊 Updated taxonomy has {len(updated_taxonomy)} categories")

    # Show sample
    print("\n📋 Sample categories:")
    for _i, (category, types) in enumerate(list(updated_taxonomy.items())[:3]):
        print(f"   {category}: {len(types)} types")
        if types:
            print(f"      Examples: {types[:3]}")

    print("\n✅ Taxonomy manager test completed!")
