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
from sklearn.metrics import classification_report
import re
from collections import Counter

# Database and model paths
DB_PATH = Path(__file__).parent.parent / "data" / "products.db"
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
        """Clean text for ML processing."""
        text = str(text).lower().strip()
        text = re.sub(r'[^a-z0-9 ]', '', text)
        return text

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
        """Prepare text features for ML."""
        # Combine name and brand for richer features
        df['text_features'] = df['Name'].fillna('') + ' ' + df['Brand'].fillna('')

        # Clean text
        df['text_features'] = df['text_features'].apply(self.clean_text)

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

        # Prepare features
        self.vectorizer = TfidfVectorizer(max_features=2000, ngram_range=(1, 2))  # Reduced features
        X = self.vectorizer.fit_transform(df['text_features'])

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

        # Prepare input
        text_features = self.clean_text(f"{product_name} {product_brand}")
        X = self.vectorizer.transform([text_features])

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
            'vectorizer': self.vectorizer,
            'classifier': self.classifier,
            'category_labels': self.category_labels,
            'type_labels': self.type_labels,
            'page_labels': self.page_labels
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