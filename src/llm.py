from __future__ import annotations

import os
from typing import List, Optional

from pydantic import BaseModel, Field
from src.db import Database
from dotenv import load_dotenv

load_dotenv()


class CompetitorInsight(BaseModel):
    asin: str
    title: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    rating: Optional[float]
    key_points: List[str] = Field(default_factory=list)


class AnalysisOutput(BaseModel):
    summary: str
    positioning: str
    top_competitors: List[CompetitorInsight]
    recommendations: List[str]


def _format_competitors(db: Database, parent_asin: str) -> List[dict]:
    comps = db.search_products({"parent_asin": parent_asin})
    return [
        {
            "asin": c["asin"],
            "title": c["title"],
            "price": c["price"],
            "currency": c.get("currency"),
            "rating": c["rating"],
            "amazon_domain": c.get("amazon_domain"),
        }
        for c in comps
    ]


def analyze_competition(parent_asin: str) -> str:
    from langchain_openai import ChatOpenAI
    from langchain.prompts import PromptTemplate
    from langchain_core.output_parsers import PydanticOutputParser

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "Set OPENAI_API_KEY to run LLM analysis."

    db = Database()
    product = db.get_product(parent_asin)
    competitors = _format_competitors(db, parent_asin)

    parser = PydanticOutputParser(pydantic_object=AnalysisOutput)

    template = (
        "You are a market analyst. Given a product and its competitor list, "
        "write a concise analysis. Pay attention to currency and pricing context.\n\n"
        "Product Title: {product_title}\n"
        "Brand: {brand}\n"
        "Price: {currency} {price}\n"
        "Rating: {rating}\n"
        "Categories: {categories}\n"
        "Amazon Domain: {amazon_domain}\n\n"
        "Competitors (JSON): {competitors}\n\n"
        "IMPORTANT: All prices should be displayed with their correct currency symbol. "
        "When comparing prices, ensure you're using the same currency context.\n\n"
        "{format_instructions}"
    )

    prompt = PromptTemplate(
        template=template,
        input_variables=["product_title", "brand", "price", "currency", "rating", "categories", "amazon_domain", "competitors"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    llm = ChatOpenAI(model="gpt-4", temperature=0)

    chain = prompt | llm | parser

    result: AnalysisOutput = chain.invoke(
        {
            "product_title": product["title"] if product else parent_asin,
            "brand": product.get("brand") if product else None,
            "price": product.get("price") if product else None,
            "currency": product.get("currency") if product else "",
            "rating": product.get("rating") if product else None,
            "categories": product.get("categories") if product else None,
            "amazon_domain": product.get("amazon_domain") if product else "com",
            "competitors": competitors,
        }
    )

    # Present as plain text for Streamlit
    lines = [
        "Summary:\n" + result.summary,
        "\nPositioning:\n" + result.positioning,
        "\nTop Competitors:",
    ]
    for c in result.top_competitors[:5]:
        pts = "; ".join(c.key_points) if c.key_points else ""
        # Use the competitor's currency or fall back to generic formatting
        currency = c.currency if c.currency else ""
        price_str = f"{currency} {c.price}" if currency and c.price else f"${c.price}" if c.price else "N/A"
        lines.append(f"- {c.asin} | {c.title} | {price_str} | ⭐ {c.rating} {pts}")
    if result.recommendations:
        lines.append("\nRecommendations:")
        for r in result.recommendations:
            lines.append(f"- {r}")

    return "\n".join(lines)


