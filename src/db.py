from tinydb import TinyDB, Query
from typing import Dict, List, Optional, Any
from datetime import datetime
import os


class Database:
    def __init__(self, db_path: str = "data.json"):
        # Create data directory if db_path has a directory component
        dirname = os.path.dirname(db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self.db = TinyDB(db_path)
        self.products = self.db.table('products')

    def insert_product(self, product_data: Dict[str, Any]) -> int:
        """Insert a new product into the database."""
        product_data['created_at'] = datetime.now().isoformat()
        return self.products.insert(product_data)

    def get_product(self, asin: str) -> Optional[Dict[str, Any]]:
        """Get a product by its ASIN."""
        Product = Query()
        return self.products.get(Product.asin == asin)

    def get_all_products(self) -> List[Dict[str, Any]]:
        """Get all products from the database."""
        return self.products.all()

    def search_products(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search products based on criteria (e.g., {"parent_asin": "B123"})."""
        Product = Query()
        query = None
        for key, value in search_criteria.items():
            if query is None:
                query = (Product[key] == value)
            else:
                query &= (Product[key] == value)
        return self.products.search(query) if query else []