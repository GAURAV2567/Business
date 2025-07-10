import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import altair as alt
import plotly.express as px

st.set_page_config(page_title="Fishing Collection Dashboard", layout="wide",initial_sidebar_state="expanded")

# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_csv("Final.csv")
    fishing_df = df[df['collection'].str.lower().str.contains("fishing")]
    fishing_df['avg_rating'] = fishing_df['avg_rating'].fillna(0)
    fishing_df['review_count'] = fishing_df['review_count'].fillna(0).astype(int)
    return fishing_df

df = load_data()

st.write('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)

#st.title("Fishing Collection Dashboard") 
st.markdown(
        f"<center><p style=' font-weight: bold;"
        f"font-size: 50px;'>Fishing Collection Dashboard</p></center>",
        unsafe_allow_html=True,
)

# --- Sidebar Filters ---
st.sidebar.header("Filters")
sub_collections = sorted(df['sub_collection'].dropna().unique())
selected_subs = st.sidebar.multiselect("Sub-Collection", sub_collections, default=sub_collections)
review_range = st.sidebar.slider("Review Count", 0, int(df['review_count'].max()), (0, 81))
rating_range = st.sidebar.slider("Rating", 0.0, 5.0, (0.0, 5.0), 0.1)

filtered_df = df[
    df['sub_collection'].isin(selected_subs) &
    df['review_count'].between(*review_range) &
    df['avg_rating'].between(*rating_range)
]

# --- KPI Metrics ---
total_products = len(filtered_df)
reviewed_products = (filtered_df['review_count'] > 0).sum()
review_coverage = reviewed_products / total_products * 100 if total_products else 0
avg_rating = filtered_df['avg_rating'].mean() if reviewed_products else 0
most_reviewed = filtered_df.sort_values("review_count", ascending=False).iloc[0] if not filtered_df.empty else None

col1, col2, col3, col4 = st.columns(4)
col1.metric("TOTAL PRODUCTS", f"{total_products}")
col2.metric("% NO REVIEWS", f"{100 - review_coverage:.0f}%")
col3.metric("AVERAGE RATING", f"{avg_rating:.2f} ⭐")
col4.metric("MOST REVIEWED", most_reviewed['title'] if most_reviewed is not None else "N/A")

st.markdown("---")

# --- Bar Chart Columns ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("Number of Reviews per Sub-Collection")
    sub_reviews = (
        filtered_df.groupby('sub_collection')['review_count']
        .sum()
        .sort_values(ascending=True)
        .reset_index()
    )
    fig_bar = px.bar(sub_reviews, x='review_count', y='sub_collection', orientation='h')
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.subheader("No. of Products vs Reviews")
    sub_metrics = (
        filtered_df.groupby('sub_collection')
        .agg(product_count=('title', 'count'), total_reviews=('review_count', 'sum'))
        .reset_index()
    )
    sub_metrics["perct"] = round(((sub_metrics["total_reviews"] / sub_metrics["product_count"])*100 )- 100,2) 
    sub_metrics["perct"] = sub_metrics["perct"].apply(lambda x: "Reviewed "+ str(x) + "% more" if x >0 else "Reviewed "+ str(x*-1) + "% less")
    fig_comp = px.scatter(sub_metrics, x='product_count', y='total_reviews', #title='No. of Products vs Reviews',
                          size="total_reviews", color="sub_collection",size_max=30,hover_name='perct',
                          )
    fig_comp.update_layout(
        xaxis=dict(range=[0, 1300]),
        yaxis=dict(range=[0, 1300]),
        width=500,
        height=500
             )
    
    st.plotly_chart(fig_comp, use_container_width=True)


# --- Word Cloud ---
st.subheader("Common Words in Product Titles")
text = ' '.join(filtered_df['title'].dropna())
wc = WordCloud(width=800, height=300, background_color='white').generate(text)
fig, ax = plt.subplots(figsize=(10, 3))
ax.imshow(wc, interpolation='bilinear')
ax.axis('off')
st.pyplot(fig)

# --- Scatter Plot ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Engagement vs Satisfaction")
    chart_data = filtered_df[['title', 'review_count', 'avg_rating']].dropna()
    #st.dataframe(chart_data)
    st.altair_chart(
        alt.Chart(chart_data).mark_circle(size=60).encode(
            x='avg_rating',
            y='review_count',
            tooltip=['title', 'review_count', 'avg_rating'],
            color=alt.value("#1f77b4")
        ).interactive().properties(height=400),
        use_container_width=True
    )

with col2:
    st.subheader("Worst Performing Products")
    worst_df = chart_data.copy()
    worst_df = worst_df[worst_df["review_count"]>0].reset_index(drop=True)
    worst_df = worst_df[worst_df["avg_rating"]<=3].reset_index(drop=True)
    worst_df['score'] = (worst_df['review_count'] / (worst_df['avg_rating'] + 1e-6)) + worst_df['review_count'] - (worst_df['avg_rating']*2)
    worst = worst_df.sort_values(by=['score'], ascending=False).head(8)[['title', 'review_count', 'avg_rating']].reset_index(drop=True)
    st.table(worst.rename(columns={
        'title': 'Product Title',
        'review_count': 'Reviews',
        'avg_rating': 'Avg Rating'
    }))

