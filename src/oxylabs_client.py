from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


OXYLABS_BASE_URL = "https://realtime.oxylabs.io/v1/queries"


def _extract_content(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Oxylabs may return {"results":[{"content":{...}}]} or directly a dict
    if isinstance(payload, dict):
        if "results" in payload and isinstance(payload["results"], list) and payload["results"]:
            first = payload["results"][0]
            if isinstance(first, dict) and "content" in first:
                return first["content"] or {}
        if "content" in payload:
            return payload.get("content") or {}
    return payload


def _normalize_product(content: Dict[str, Any]) -> Dict[str, Any]:
    # Get main category path
    category_path = []
    if content.get("category_path"):
        category_path = [cat.strip() for cat in content["category_path"] if cat]

    return {
        "asin": content.get("asin"),
        "url": content.get("url"),
        "brand": content.get("brand"),
        "price": content.get("price"),
        "stock": content.get("stock"),
        "title": content.get("title"),
        "rating": content.get("rating"),
        "images": content.get("images", []),
        "categories": content.get("category", []) or content.get("categories", []),
        "category_path": category_path,
        "currency": content.get("currency"),
        "buybox": content.get("buybox", []),
        "product_overview": content.get("product_overview", []),
    }


def _post_query(payload: Dict[str, Any]) -> Dict[str, Any]:
    username = os.getenv("OXYLABS_USERNAME", "").strip()
    password = os.getenv("OXYLABS_PASSWORD", "").strip()
    
    response = requests.post(OXYLABS_BASE_URL, auth=(username, password), json=payload)
    response.raise_for_status()
    response_json = response.json()
    
    return response_json


def scrape_product_details(asin: str, geo_location: str, domain: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "source": "amazon_product",
        "query": asin,
        "geo_location": geo_location,
        "parse": True,
        "domain": domain,
    }
    raw = _post_query(payload)
    content = _extract_content(raw)
    normalized = _normalize_product(content)
    if not normalized.get("asin"):
        # fallback inject asin
        normalized["asin"] = asin
    
    # Add domain and geo_location to track search context
    normalized["amazon_domain"] = domain
    normalized["geo_location"] = geo_location
    return normalized


def _clean_search_title(title: str) -> str:
    """Remove common separators from title to get main product name."""
    if " - " in title:
        title = title.split(" - ")[0]
    if "|" in title:
        title = title.split("|")[0]
    return title.strip()


def _extract_search_results(content: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract both organic and sponsored results from search response."""
    items = []
    if not isinstance(content, dict):
        return items
        
    if "results" in content:
        results = content["results"]
        if isinstance(results, dict):
            # Add organic results
            if "organic" in results:
                items.extend(results["organic"])
            # Add sponsored results
            if "paid" in results:
                items.extend(results["paid"])
    elif "products" in content and isinstance(content["products"], list):
        items.extend(content["products"])
        
    return items


def _normalize_search_result(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract relevant fields from a search result item."""
    asin = item.get("asin") or item.get("product_asin")
    title = item.get("title")
    
    if not (asin and title):
        return None
        
    return {
        "asin": asin,
        "title": title,
        "category": item.get("category"),
        "price": item.get("price"),
        "rating": item.get("rating")
    }


def search_competitors(
    query_title: str,
    domain: str,
    categories: Optional[List[str]] = None,
    pages: int = 1,
    geo_location: str = "",
) -> List[Dict[str, Any]]:
    """Search for competitor products using multiple strategies."""
    st.write("🔍 Searching for competitors...")
    
    search_title = _clean_search_title(query_title)
    results: List[Dict[str, Any]] = []
    seen_asins = set()
    
    # Define search strategies
    strategies = ["featured", "price_asc", "price_desc", "avg_rating"]
    
    for sort_by in strategies:
        for page in range(1, max(1, pages) + 1):
            # Prepare search request
            payload = {
                "source": "amazon_search",
                "query": search_title,
                "parse": True,
                "domain": domain,
                "page": page,
                "sort_by": sort_by,
                "geo_location": geo_location,
            }
            
            # Add category if available
            if categories and categories[0]:
                payload["refinements"] = {"category": categories[0]}
            
            # Execute search
            content = _extract_content(_post_query(payload))
            items = _extract_search_results(content)
            
            # Process results
            for item in items:
                result = _normalize_search_result(item)
                if result and result["asin"] not in seen_asins:
                    seen_asins.add(result["asin"])
                    results.append(result)
            
            time.sleep(0.3)
    
    st.write(f"✅ Found {len(results)} competitors")
    return results


def scrape_multiple_products(asins: List[str], geo_location: str, domain: str) -> List[Dict[str, Any]]:
    st.write("🔍 Scraping competitor details...")
    products: List[Dict[str, Any]] = []
    
    # Create a progress bar
    progress_text = st.empty()
    progress_bar = st.progress(0)
    total = len(asins)
    
    for idx, a in enumerate(asins, 1):
        try:
            # Update progress
            progress_text.write(f"🔄 Processing competitor {idx}/{total}: {a}")
            progress_bar.progress(idx/total)
            
            product = scrape_product_details(asin=a, geo_location=geo_location, domain=domain)
            products.append(product)
            progress_text.write(f"✅ Found: {product.get('title', a)}")
        except Exception as e:
            progress_text.write(f"❌ Failed to scrape {a}")
            continue
        time.sleep(0.3)
    
    # Clear progress indicators
    progress_text.empty()
    progress_bar.empty()
    
    st.write(f"✅ Successfully scraped {len(products)} out of {total} competitors")
    return products