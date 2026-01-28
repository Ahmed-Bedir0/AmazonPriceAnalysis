import streamlit as st
from typing import Optional

from src.db import Database
from src.llm import analyze_competition
from src.services import scrape_and_store_product, fetch_and_store_competitors

def render_header() -> None:
    st.title("🛒 Amazon Competitor Analysis (Egypt Edition)")
    st.caption("Advanced scraping and analysis tool using Oxylabs, TinyDB, and LangChain")

def render_inputs() -> tuple[str, str, str]:
    # Set columns for better input layout
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        asin = st.text_input("Product ASIN", placeholder="e.g., B09YRS594P")
    with col2:
        # Defaulting to 11511 (Cairo) for Egyptian context
        geo = st.text_input("Zip/Postal Code", value="11511")
    with col3:
        # Added 'eg' and moved to top of list for your convenience
        domain = st.selectbox("Amazon domain", [
            "eg", "com", "ae", "ca", "co.uk", "de", "fr", "it", "es"
        ], index=0)
        
    return asin.strip(), geo.strip(), domain

def render_product_card(product: dict) -> None:
    with st.container(border=True):
        cols = st.columns([1, 2])
        
        # Image column
        try:
            images = product.get("images", [])
            if images and len(images) > 0:
                cols[0].image(images[0], use_container_width=True)
            else:
                cols[0].info("No image available")
        except Exception:
            cols[0].error("Error loading image")
            
        # Info column
        with cols[1]:
            st.subheader(product.get("title") or f"Product: {product['asin']}")
            
            info_cols = st.columns(3)
            currency = product.get('currency', 'EGP')
            price = product.get('price', '-')
            
            # Formatted price display
            display_price = f"{currency} {price:,.2f}" if isinstance(price, (int, float)) else f"{currency} {price}"
            
            info_cols[0].metric("Price", display_price)
            info_cols[1].markdown(f"**Brand:** \n{product.get('brand', '-')}")
            info_cols[2].markdown(f"**Stock:** \n{product.get('stock', '-')}")
            
            # Domain and Location metadata
            st.caption(f"🌐 amazon.{product.get('amazon_domain', 'eg')} | 📍 Location: {product.get('geo_location', 'Egypt')}")
            
            # Action buttons
            st.write(f"[View on Amazon]({product.get('url', '#')})")
            if st.button("🚀 Analyze Competitors", key=f"analyze_{product['asin']}", type="secondary"):
                st.session_state["analyzing_asin"] = product["asin"]

def main() -> None:
    st.set_page_config(page_title="Amazon Egypt Analysis", page_icon="🛒", layout="wide")
    render_header()
    asin, geo, domain = render_inputs()

    # Scrape Action
    if st.button("Scrape Product Details", type="primary") and asin:
        with st.spinner(f"Scraping {asin} from amazon.{domain}..."):
            try:
                scrape_and_store_product(asin=asin, geo_location=geo, domain=domain)
                st.success(f"Product {asin} saved to local database.")
                # Reset analysis view if a new product is scraped
                if "analyzing_asin" in st.session_state:
                    del st.session_state["analyzing_asin"]
            except Exception as e:
                st.error(f"Scraping failed: {str(e)}")

    # Database Display
    db = Database()
    products = db.get_all_products()
    
    if products:
        st.divider()
        st.subheader("📋 Your Scraped Inventory")
        
        # Pagination settings
        items_per_page = 5
        total_pages = max((len(products) + items_per_page - 1) // items_per_page, 1)
        
        col_p1, col_p2, col_p3 = st.columns([4, 1, 4])
        with col_p2:
            page = st.number_input("Page", min_value=1, max_value=total_pages, value=1) - 1
            
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(products))
        
        for p in products[start_idx:end_idx]:
            render_product_card(p)

    # Competitor Analysis Section
    selected_asin: Optional[str] = st.session_state.get("analyzing_asin")
    if selected_asin:
        st.divider()
        st.subheader(f"🔍 Competition Deep-Dive: {selected_asin}")
        
        db = Database()
        existing_comps = db.search_products({"parent_asin": selected_asin})
        
        if not existing_comps:
            with st.spinner("Searching for competitors in Egypt market..."):
                comps = fetch_and_store_competitors(
                    parent_asin=selected_asin,
                    domain=domain,
                    geo_location=geo,
                    pages=2,
                )
                st.success(f"Discovered {len(comps)} new competitors.")
        else:
            st.info(f"Loaded {len(existing_comps)} competitors from local cache.")
            
        act_col1, act_col2 = st.columns([3, 1])
        with act_col2:
            if st.button("🔄 Refresh Data"):
                with st.spinner("Updating competitor prices..."):
                    fetch_and_store_competitors(
                        parent_asin=selected_asin,
                        domain=domain,
                        geo_location=geo,
                        pages=2,
                    )
                    st.rerun()
        
        with act_col1:
            if st.button("🤖 Run AI Price Analysis", type="primary"):
                with st.spinner("LLM is processing market trends..."):
                    analysis_text = analyze_competition(parent_asin=selected_asin)
                    st.info("AI Analysis Result:")
                    st.markdown(analysis_text)

if __name__ == "__main__":
    main()
