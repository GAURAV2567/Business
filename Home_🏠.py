import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import re

# 2. Page config
st.set_page_config(page_title="Catalog Dashboard", layout="wide",page_icon="🏠",initial_sidebar_state="expanded")

# 1. Load scraped JSON
# Load hierarchical product data
@st.cache_data
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

# Load Sub_collection_categories.json
with open("Sub_collection_categories.json", "r", encoding="utf-8") as f:
    subcat_json = json.load(f)

# Build mapping: sub_title -> parent title (i.e., sub_collection)
sub_title_to_parent = {}
for category in subcat_json.values():
    parent_title = category["title"]
    for sub_key, sub_title in category["subs"].items():
        sub_title_to_parent[sub_title] = parent_title

# Apply mapping to df['sub_title']
df["sub_collection"] = df["sub_title"].map(sub_title_to_parent).fillna("Unknown")

df = df.drop(['parent_handle','sub_handle'], axis=1)

#st.dataframe(df)
st.write('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)

st.markdown(
        f"<center><p style=' font-weight: bold;"
        f"font-size: 50px;'>Cabral Outdoors</p></center>",
        unsafe_allow_html=True,
)

col1, col2 = st.columns([3,1])

#col1.title("Cabral Outdoors Catalog")
no_review_count = int((df['review_count'] == 0).sum())
#col2.subheader(" ")
col2.markdown(f"##### **:red[~~{no_review_count}] products have no reviews**", unsafe_allow_html=True)

#st.dataframe(df)

# 3. Sidebar filters
st.sidebar.header("Filters")
collections = st.sidebar.multiselect("Collection", options=sorted(df["collection"].unique()), default=sorted(df["collection"].unique()))
price_min, price_max = st.sidebar.slider(
    "Price range",
    int(df["price"].min()), int(df["price"].max()),
    (int(df["price"].min()), int(df["price"].max()))
)
review_min = st.sidebar.slider("Min reviews", 0, int(df["review_count"].max()), (0, 81))

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

st.subheader("Number of Products Per Collection")
bar_data = df["collection"].value_counts(ascending=True).reset_index()
bar_data.columns = ["Collection", "Count"]
st.plotly_chart(px.bar(bar_data, x="Count", y="Collection", orientation='h', height=300),)


# 5. Charts
chart_col, hist_col = st.columns(2)
with chart_col:
    st.subheader("Top 5 Most Reviewed Products")
    top5 = filtered.sort_values("review_count", ascending=False).head(5)
    st.dataframe(top5[["title", "review_count", "avg_rating"]].rename(columns={
        "title": "Product", "review_count": "Reviews", "avg_rating": "Rating"
    }),hide_index=True)
with hist_col:
    # Histogram: Price distribution
    st.subheader("Price Distribution")
    df = df[df["price"]<=11000]
    hist = px.histogram(df, x="price", nbins=50, template="plotly_white",height=300)
    hist.update_traces(marker=dict(line=dict(width=1, color='white')))
    hist.update_layout(xaxis_title=None, yaxis_title=None)
    st.plotly_chart(hist)

