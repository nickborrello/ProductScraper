"""
AI-Powered Product Classification Module
Uses machine learning to classify products based on trained models.
"""

import os
import pandas as pd
import sqlite3
from pathlib import Path
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multioutput import MultiOutputClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score
import re
from collections import Counter
from scipy.sparse import hstack

# Database and model paths
DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "databases" / "products.db"
MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

class AIProductClassifier:
    """AI-powered product classifier using machine learning."""

    def __init__(self):
        self.vectorizer = None
        self.classifier = None
        self.category_labels = []
        self.type_labels = []
        self.page_labels = []

    def clean_text(self, text):
        """Clean text for ML processing with enhanced pet-specific preprocessing."""
        text = str(text).lower().strip()

        # Remove common noise patterns
        text = re.sub(r'[^\w\s]', ' ', text)  # Replace punctuation with spaces
        text = re.sub(r'\s+', ' ', text)      # Normalize whitespace

        # Pet-specific abbreviations and expansions
        pet_abbreviations = {
            'lb': 'pound', 'lbs': 'pounds', 'oz': 'ounce', 'kg': 'kilogram',
            'kitten': 'cat', 'puppy': 'dog', 'canine': 'dog', 'feline': 'cat',
            'adult': '', 'junior': '', 'senior': '', 'all life stages': '',
            'dry': '', 'wet': '', 'canned': '', 'raw': '', 'freeze dried': '',
            'chicken': 'poultry', 'turkey': 'poultry', 'beef': 'meat', 'fish': 'seafood',
            'salmon': 'seafood', 'tuna': 'seafood', 'lamb': 'meat'
        }

        for abbr, expansion in pet_abbreviations.items():
            text = re.sub(r'\b' + re.escape(abbr) + r'\b', expansion, text)

        # Extract and preserve important numbers (weights, ages)
        weight_pattern = r'(\d+(?:\.\d+)?)\s*(lb|pound|pounds|oz|ounce|kg|kilogram)'
        weights = re.findall(weight_pattern, text)
        if weights:
            text += f" weight_{weights[0][1]}"  # Add weight unit as feature

        # Remove stopwords but keep pet-specific important words
        important_words = {
            'dog', 'cat', 'bird', 'fish', 'reptile', 'small', 'animal', 'pet',
            'food', 'treat', 'toy', 'bed', 'bowl', 'cage', 'litter', 'grooming',
            'health', 'care', 'supplies', 'equipment', 'feed', 'seed'
        }

        basic_stopwords = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'an', 'a', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'shall'
        }

        tokens = []
        for word in text.split():
            if word not in basic_stopwords or word in important_words:
                tokens.append(word)

        return ' '.join(tokens)

    def load_training_data(self):
        """Load classified products from database for training."""
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found: {DB_PATH}")

        conn = sqlite3.connect(DB_PATH)
        try:
            # Get products with classifications (limit for faster training)
            cursor = conn.execute("""
                SELECT Name, Brand, Category, Product_Type, Product_On_Pages
                FROM products
                WHERE Category IS NOT NULL AND Category != ''
                  AND Product_Type IS NOT NULL AND Product_Type != ''
                ORDER BY RANDOM() LIMIT 5000  -- Sample for faster training
            """)

            rows = cursor.fetchall()
            if not rows:
                raise ValueError("No classified products found for training")

            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=['Name', 'Brand', 'Category', 'Product_Type', 'Product_On_Pages'])

            print(f"✅ Loaded {len(df)} products for training (sampled)")
            return df

        finally:
            conn.close()

    def prepare_features(self, df):
        """Prepare text features for ML with enhanced pet-specific features."""
        # Combine name and brand for richer features
        df['text_features'] = df['Name'].fillna('') + ' ' + df['Brand'].fillna('')

        # Clean text
        df['text_features'] = df['text_features'].apply(self.clean_text)

        # Extract pet type features
        pet_types = ['dog', 'cat', 'bird', 'fish', 'reptile', 'small animal', 'horse']
        for pet in pet_types:
            df[f'pet_{pet.replace(" ", "_")}'] = df['text_features'].str.contains(pet).astype(int)

        # Extract food type features
        food_types = ['dry', 'wet', 'raw', 'canned', 'treat', 'kibble', 'formula']
        for food in food_types:
            df[f'food_{food}'] = df['text_features'].str.contains(food).astype(int)

        # Extract product category hints
        category_hints = ['food', 'treat', 'toy', 'bed', 'bowl', 'cage', 'litter', 'grooming', 'health']
        for hint in category_hints:
            df[f'category_{hint}'] = df['text_features'].str.contains(hint).astype(int)

        return df

    def prepare_labels(self, df):
        """Prepare multi-label targets."""
        # Category labels (single label per product)
        self.category_labels = sorted(df['Category'].unique())

        # Product Type labels (single label per product)
        self.type_labels = sorted(df['Product_Type'].unique())

        # Page labels (multi-label - products can be on multiple pages)
        all_pages = []
        for pages in df['Product_On_Pages'].dropna():
            # Split on pipe and comma to get individual pages
            page_list = str(pages).replace('|', ',').split(',')
            all_pages.extend([p.strip() for p in page_list if p.strip()])

        # Get top 50 most common pages (reduced for faster training)
        page_counts = Counter(all_pages)
        self.page_labels = [page for page, _ in page_counts.most_common(50)]

        print(f"📊 Categories: {len(self.category_labels)}")
        print(f"📊 Product Types: {len(self.type_labels)}")
        print(f"📊 Pages: {len(self.page_labels)}")

        return df

    def encode_labels(self, df):
        """Encode labels for training."""
        # Category encoding (single-label)
        category_map = {cat: i for i, cat in enumerate(self.category_labels)}
        df['category_encoded'] = df['Category'].map(category_map)

        # Product Type encoding (single-label)
        type_map = {typ: i for i, typ in enumerate(self.type_labels)}
        df['type_encoded'] = df['Product_Type'].map(type_map)

        # Pages encoding (multi-label binary) - use pd.concat for efficiency
        page_cols = []
        for page in self.page_labels:
            col_name = f'page_{page.replace(" ", "_").replace("&", "and")}'
            page_cols.append(pd.Series(
                df['Product_On_Pages'].apply(lambda x: 1 if page in str(x).replace('|', ',') else 0),
                name=col_name
            ))

        if page_cols:
            pages_df = pd.concat(page_cols, axis=1)
            df = pd.concat([df, pages_df], axis=1)

        return df

    def train(self):
        """Train the AI classifier."""
        print("🤖 Training AI Product Classifier...")

        # Load and prepare data
        df = self.load_training_data()
        df = self.prepare_features(df)
        df = self.prepare_labels(df)
        df = self.encode_labels(df)

        # Prepare features - combine TF-IDF with binary features
        text_vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        X_text = text_vectorizer.fit_transform(df['text_features'])

        # Get binary features
        binary_cols = [col for col in df.columns if col.startswith(('pet_', 'food_', 'category_'))]
        X_binary = df[binary_cols].values

        # Combine features
        X = hstack([X_text, X_binary])

        print(f"📊 Feature matrix shape: {X.shape} (text: {X_text.shape[1]}, binary: {X_binary.shape[1]})")

        # Prepare targets
        y_category = df['category_encoded'].values
        y_type = df['type_encoded'].values

        # Multi-label target for pages
        page_cols = [f'page_{page.replace(" ", "_").replace("&", "and")}' for page in self.page_labels]
        y_pages = df[page_cols].values

        # Split data
        X_train, X_test, y_cat_train, y_cat_test, y_type_train, y_type_test, y_pages_train, y_pages_test = \
            train_test_split(X, y_category, y_type, y_pages, test_size=0.2, random_state=42)

        print(f"📈 Training on {X_train.shape[0]} samples, testing on {X_test.shape[0]} samples")

        # Use faster LogisticRegression instead of RandomForest
        print("🏷️ Training category classifier...")
        cat_clf = LogisticRegression(max_iter=1000, random_state=42)
        cat_clf.fit(X_train, y_cat_train)

        print("🏷️ Training product type classifier...")
        type_clf = LogisticRegression(max_iter=1000, random_state=42)
        type_clf.fit(X_train, y_type_train)

        print("🏷️ Training pages classifier...")
        pages_clf = MultiOutputClassifier(LogisticRegression(max_iter=500, random_state=42))
        pages_clf.fit(X_train, y_pages_train)

        # Combine classifiers
        self.classifier = {
            'category': cat_clf,
            'type': type_clf,
            'pages': pages_clf
        }

        # Quick evaluation
        print("📊 Quick evaluation...")
        cat_pred = cat_clf.predict(X_test)
        type_pred = type_clf.predict(X_test)

        cat_accuracy = np.mean(cat_pred == y_cat_test)
        type_accuracy = np.mean(type_pred == y_type_test)

        # Calculate F1 scores for better evaluation
        cat_f1 = f1_score(y_cat_test, cat_pred, average='weighted')
        type_f1 = f1_score(y_type_test, type_pred, average='weighted')

        print(".2f")
        print(".2f")
        print(".2f")
        print(".2f")

        # Save model
        self.save_model()

        print("✅ AI classifier trained and saved!")
        return self

    def predict(self, product_name, product_brand=''):
        """Predict classifications for a product."""
        if not self.classifier:
            raise ValueError("Model not trained. Call train() first.")

        # Prepare input - combine text and binary features
        text_features = self.clean_text(f"{product_name} {product_brand}")
        X_text = self.vectorizer.transform([text_features])

        # Extract binary features for this product
        binary_features = []
        pet_types = ['dog', 'cat', 'bird', 'fish', 'reptile', 'small animal', 'horse']
        for pet in pet_types:
            binary_features.append(1 if pet in text_features else 0)

        food_types = ['dry', 'wet', 'raw', 'canned', 'treat', 'kibble', 'formula']
        for food in food_types:
            binary_features.append(1 if food in text_features else 0)

        category_hints = ['food', 'treat', 'toy', 'bed', 'bowl', 'cage', 'litter', 'grooming', 'health']
        for hint in category_hints:
            binary_features.append(1 if hint in text_features else 0)

        X_binary = [binary_features]  # Make it 2D
        X = hstack([X_text, X_binary])

        # Predict
        category_idx = self.classifier['category'].predict(X)[0]
        type_idx = self.classifier['type'].predict(X)[0]
        pages_binary = self.classifier['pages'].predict(X)[0]

        # Decode predictions
        predicted_category = self.category_labels[category_idx]
        predicted_type = self.type_labels[type_idx]

        # Get predicted pages (where binary prediction is 1)
        predicted_pages = [page for page, pred in zip(self.page_labels, pages_binary) if pred == 1]

        return {
            'Category': [predicted_category],
            'Product Type': [predicted_type.title()],  # Normalize case
            'Product On Pages': predicted_pages[:3]  # Top 3 pages
        }

    def save_model(self):
        """Save trained model to disk."""
        model_data = {
            'vectorizer': self.vectorizer,  # This is now just the text vectorizer
            'classifier': self.classifier,
            'category_labels': self.category_labels,
            'type_labels': self.type_labels,
            'page_labels': self.page_labels,
            'feature_info': {
                'pet_types': ['dog', 'cat', 'bird', 'fish', 'reptile', 'small animal', 'horse'],
                'food_types': ['dry', 'wet', 'raw', 'canned', 'treat', 'kibble', 'formula'],
                'category_hints': ['food', 'treat', 'toy', 'bed', 'bowl', 'cage', 'litter', 'grooming', 'health']
            }
        }

        model_path = MODEL_DIR / 'ai_classifier.pkl'
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)

        print(f"💾 Model saved to {model_path}")

    def load_model(self):
        """Load trained model from disk."""
        model_path = MODEL_DIR / 'ai_classifier.pkl'
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)

        self.vectorizer = model_data['vectorizer']
        self.classifier = model_data['classifier']
        self.category_labels = model_data['category_labels']
        self.type_labels = model_data['type_labels']
        self.page_labels = model_data['page_labels']

        print("📂 Model loaded successfully")
        return self


# Global AI classifier instance
ai_classifier = None

def get_ai_classifier():
    """Get or create AI classifier instance."""
    global ai_classifier
    if ai_classifier is None:
        ai_classifier = AIProductClassifier()
        try:
            ai_classifier.load_model()
            print("✅ AI classifier loaded from disk")
        except FileNotFoundError:
            print("🤖 Training new AI classifier...")
            ai_classifier.train()
    return ai_classifier

def classify_product_ai(product_info):
    """
    Classify a product using AI instead of fuzzy matching.

    Args:
        product_info: Dict with product details (Name, Brand, etc.)

    Returns:
        Dict with AI-predicted classifications
    """
    product_name = product_info.get('Name', '').strip()
    product_brand = product_info.get('Brand', '').strip()

    if not product_name:
        return {}

    try:
        classifier = get_ai_classifier()
        predictions = classifier.predict(product_name, product_brand)

        # Format like the existing system
        result = {}
        for label, items in predictions.items():
            if items:
                result[label] = "|".join(items)
            else:
                result[label] = ""

        return result

    except Exception as e:
        print(f"⚠️ AI classification failed: {e}")
        return {}


# Test the AI classifier
if __name__ == "__main__":
    print("🧠 Testing AI Product Classifier")
    print("=" * 50)

    # Test product
    test_product = {
        'Name': 'Purina Pro Plan Adult Dog Food Chicken & Rice Formula',
        'Brand': 'Purina'
    }

    print("📦 Test Product:")
    print(f"   Name: {test_product['Name']}")
    print(f"   Brand: {test_product['Brand']}")
    print()

    # Classify with AI
    print("🤖 AI Classification:")
    ai_result = classify_product_ai(test_product)
    for key, value in ai_result.items():
        print(f"   {key}: {value}")

    print("\n✅ AI classification test completed!")