import streamlit as st
from google.cloud.retail import SearchRequest, SearchServiceClient
import google.auth

# Initialize authentication
project_id = google.auth.default()[1]


# Function to create search request
def get_search_request(query: str):
    default_search_placement = (
        f"projects/{project_id}/locations/global/catalogs/default_catalog/placements/default_search"
    )

    search_request = SearchRequest()
    search_request.placement = default_search_placement  # Placement is used to identify the Serving Config name.
    search_request.query = query
    search_request.visitor_id = "123456"  # A unique identifier to track visitors
    search_request.page_size = 10

    return search_request


# Function to perform search
def perform_search(query: str):
    search_request = get_search_request(query)
    search_response = SearchServiceClient().search(search_request)
    return search_response


# Initialize session state for search results
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "query" not in st.session_state:
    st.session_state.query = ""

# Streamlit app
st.title("E-Commerce Product Search")

# Input field for search query
query = st.text_input("Search for products", value=st.session_state.query)

if st.button("Search"):
    if query:
        # Perform the search and save results in session state
        st.session_state.query = query
        st.session_state.search_results = perform_search(query)
        st.info(f"Searching for: {query}")
    else:
        st.warning("Please enter a query to search.")

# Display search results in a grid layout
if st.session_state.search_results and st.session_state.search_results.results:
    st.subheader("Search Results")

    # Create columns for a grid layout
    results = st.session_state.search_results.results
    num_columns = 3  # Number of columns per row
    for idx, result in enumerate(results):
        if idx % num_columns == 0:  # Create a new row
            cols = st.columns(num_columns)
        with cols[idx % num_columns]:
            product = result.product
            primary_title = product.title if product.title else "No Title Available"

            # Display product image
            if product.images:
                st.image(
                    product.images[0].uri,
                    caption=f"{primary_title}",
                    use_column_width=True,
                )
            else:
                st.write("No Image Available")

            # Display product information
            st.markdown(f"**{primary_title}**")
            st.write(f"**Product ID**: {result.id}")
            st.markdown("---")

# Sidebar for Product Detail Emulation
st.sidebar.header("Product Detail")
selected_product_id = st.sidebar.text_input("Enter Product ID to View Details", value="")
if st.sidebar.button("View Details"):
    if selected_product_id and st.session_state.search_results:
        # Emulate showing product detail page
        st.sidebar.markdown(f"### Product Detail for ID: {selected_product_id}")
        for result in st.session_state.search_results.results:
            if result.id == selected_product_id:
                product = result.product

                # Extract primary product title
                primary_title = product.title if product.title else "No Title Available"
                st.sidebar.write(f"**Product Name**: {primary_title}")

                # Display product image
                if product.images:
                    st.sidebar.image(
                        product.images[0].uri,
                        caption=f"{primary_title}",
                        use_column_width=True,
                    )
                else:
                    st.sidebar.write("No Image Available")

                # Display variants if available
                if product.variants:
                    st.sidebar.write("**Variants:**")
                    for variant in product.variants:
                        variant_title = variant.title if variant.title else "No Title Available"
                        st.sidebar.markdown(f"#### Variant: {variant_title}")
                        if variant.images:
                            st.sidebar.image(
                                variant.images[0].uri,
                                caption=f"{variant_title}",
                                use_column_width=True,
                            )
                        st.sidebar.write(f"- **Variant ID**: {variant.id}")
                        st.sidebar.write(f"- **Colors**: {variant.color_info.colors}")
                        st.sidebar.write(f"- **Color Families**: {variant.color_info.color_families}")
    else:
        st.sidebar.warning("Please enter a product ID.")

