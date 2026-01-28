from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from src.db import Database
from src.oxylabs_client import (
    scrape_product_details,
    search_competitors,
    scrape_multiple_products,
)


def scrape_and_store_product(asin: str, geo_location: str, domain: str) -> Dict[str, Any]:
    data = scrape_product_details(asin=asin, geo_location=geo_location, domain=domain)
    db = Database()
    return db.insert_product(data)


def fetch_and_store_competitors(
    parent_asin: str,
    domain: str,
    geo_location: str,
    pages: int = 2,
) -> List[Dict[str, Any]]:
    # Load parent product details for better search
    db = Database()
    parent = db.get_product(parent_asin)
    if not parent:
        return []
    
    # Use parent product's domain and geo_location if available
    search_domain = parent.get("amazon_domain", domain)
    search_geo = parent.get("geo_location", geo_location)
    st.write(f"🌍 Using domain: {search_domain}, location: {search_geo}")
        
    # Get all possible categories for searching
    search_categories = []
    if parent.get("categories"):
        search_categories.extend(str(cat) for cat in parent["categories"] if cat)
    if parent.get("category_path"):
        search_categories.extend(str(cat) for cat in parent["category_path"] if cat)
    
    # Remove duplicates and empty categories
    search_categories = list(set(
        cat.strip() 
        for cat in search_categories 
        if cat and isinstance(cat, str) and cat.strip()
    ))
    
    # Search in each category
    all_results = []
    for category in search_categories[:3]:  # Limit to top 3 categories to avoid too many requests
        search_results = search_competitors(
            query_title=parent["title"],
            domain=search_domain,
            categories=[category],
            pages=pages,
            geo_location=search_geo,
        )
        all_results.extend(search_results)
    
    # Get unique ASINs excluding the parent product
    competitor_asins = list(set(
        r.get("asin") for r in all_results 
        if r.get("asin") and r.get("asin") != parent_asin
    ))
    
    # Fetch full details for each competitor using same domain/location
    product_details = scrape_multiple_products(competitor_asins[:20], geo_location=search_geo, domain=search_domain)  # Limit to top 20 competitors
    
    # Store competitors with relationship to parent
    stored_competitors = []
    for comp in product_details:
        comp["parent_asin"] = parent_asin
        db.insert_product(comp)
        stored_competitors.append(comp)
    
    # Display competitor summary
    st.write("📊 Competitor Summary:")
    for comp in stored_competitors:
        price = comp.get("price", "N/A")
        currency = comp.get("currency", "")
        if isinstance(price, (int, float)):
            price_str = f"{currency} {price:,.2f}" if currency else f"${price:,.2f}"
        else:
            price_str = str(price)
        st.write(f"• {comp.get('title')} - {price_str}")
    st.write("---")
    
    return stored_competitors