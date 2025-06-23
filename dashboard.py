import streamlit as st
import pandas as pd
import numpy as np
import json

# 2. Page config
st.set_page_config(page_title="Catalog Dashboard", layout="wide")

# 1. Load scraped JSON
# Load hierarchical product data
#@st.cache_data
def load_data():
    with open("cabral_full_catalog_with_ratings.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    rows = []
    for parent_handle, group in raw.items():
        parent_title = group.get("title")
        for sub_handle, sub in group.get("subs", {}).items():
            sub_title = sub.get("title")
            for prod in sub.get("products", []):
                prod_data = {
                    "parent_handle": parent_handle,
                    "collection": parent_title,
                    "sub_handle": sub_handle,
                    "sub_title": sub_title,
                    "title": prod.get("title"),
                    "price": extract_price(prod.get("price")),
                    "sku": prod.get("sku"),
                    "description": prod.get("description"),
                    "url": prod.get("url"),
                    "images": prod.get("images"),
                    "review_count": prod.get("count_reviews"),
                    #"reviews": prod.get("reviews"),
                    "avg_rating": prod.get("average_rating"),

                }
                rows.append(prod_data)
    return pd.DataFrame(rows)

def extract_price(p):
    try:
        return float(p.replace("₹", "").replace(",", ""))
    except:
        return None
    
# --- Title and Callout ---
#st.title("Cabral Outdoors Catalog") 

df = load_data()

df["review_count"] = df["review_count"].fillna(0)
df["review_count"] = df["review_count"].astype(int)

df["avg_rating"] = df["avg_rating"].fillna(0.0)
df["avg_rating"] = df["avg_rating"].astype(float)


#st.dataframe(df)

col1, col2 = st.columns([3,1])

col1.title("Cabral Outdoors Catalog") 
no_review_count = int((df['review_count'] == 0).sum())
col2.subheader(" ")
col2.markdown(f"##### **:red[~~{no_review_count}] products have no reviews**", unsafe_allow_html=True)

#st.dataframe(df)

# 3. Sidebar filters
st.sidebar.header("Filters")
collections = st.sidebar.multiselect("Collection", options=sorted(df["collection"].unique()), default=sorted(df["collection"].unique()))
price_min, price_max = st.sidebar.slider(
    "Price range",
    int(df["price"].min()), int(df["price"].max()),
    (int(df["price"].min()), int(df["price"].quantile(0.75)))
)
review_min = st.sidebar.slider("Min reviews", 0, int(df["review_count"].max()), (0, 10))

# Filter data
filtered = df[
    df["collection"].isin(collections) &
    df["price"].between(price_min, price_max) &
    df["review_count"].between(review_min[0], review_min[1])
]

#st.data_editor(filtered)

# 4. KPI cards
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Products", len(filtered))
col2.metric("Average Price", f"₹{filtered['price'].mean():,.0f}")
most_reviewed = filtered.sort_values("review_count", ascending=False).iloc[0]
col3.metric("Most Reviewed", most_reviewed["title"], f"{most_reviewed['review_count']} reviews")
highest_rated = filtered.sort_values("avg_rating", ascending=False).iloc[0]
col4.metric("Highest Rated", highest_rated["title"], f"{highest_rated['avg_rating']:.1f} ⭐")

st.markdown("---")

st.subheader("Products per Collection")
by_coll = filtered["collection"].value_counts().rename_axis("collection").reset_index(name="count")
st.bar_chart(by_coll, x="collection", y="count",horizontal=True)

# 5. Charts
chart_col, hist_col = st.columns(2)
with chart_col:
    st.subheader("Top 5 Most Reviewed Products")
    top5 = filtered.sort_values("review_count", ascending=False).head(5)
    st.dataframe(top5[["title", "review_count", "avg_rating"]].rename(columns={
        "title": "Product", "review_count": "Reviews", "avg_rating": "Rating"
    }),hide_index=True)
with hist_col:
    st.subheader("Price Distribution")
    dfa = filtered["price"].value_counts().reset_index().rename(columns={"index":"price", "price": "value_counts"})
    #st.dataframe(dfa)
    st.bar_chart(dfa,x="price",y="value_counts")

