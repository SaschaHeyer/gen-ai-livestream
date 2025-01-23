# Import products into a catalog as primary products with cross-variants using Retail API
import time

import google.auth
from google.cloud.retail import (
    ColorInfo,
    ImportProductsRequest,
    PriceInfo,
    Product,
    ProductInlineSource,
    ProductInputConfig,
    ProductServiceClient,
    Image,
)

# Fetch the project ID from the Google Cloud authentication setup
project_id = google.auth.default()[1]

# Define the default catalog resource
default_catalog = f"projects/{project_id}/locations/global/catalogs/default_catalog/branches/default_branch"


# Prepare products to import as standalone primary products with cross-referenced variants
def prepare_products_with_variants():
    products = []

    # Define product details
    product_details = [
        {
            "id": "primary_case_black",
            "title": "iPhone Case Black",
            "color": "Black",
            "price": 25.0,
            "original_price": 30.0,
            "image": "https://storage.googleapis.com/doit-retail-search/black.png",
        },
        {
            "id": "primary_case_beige",
            "title": "iPhone Case Beige",
            "color": "Beige",
            "price": 26.0,
            "original_price": 32.0,
            "image": "https://storage.googleapis.com/doit-retail-search/beige.png",
        },
        {
            "id": "primary_case_yellow",
            "title": "iPhone Case Yellow",
            "color": "Yellow",
            "price": 27.0,
            "original_price": 34.0,
            "image": "https://storage.googleapis.com/doit-retail-search/yellow.png",
        },
    ]

    # Create primary products and assign all other cases as variants
    for product in product_details:
        primary_product = Product(
            id=product["id"],
            title=product["title"],
            categories=["Accessories > Phone Cases"],
            brands=["TestBrand"],
            price_info=PriceInfo(
                price=product["price"],
                original_price=product["original_price"],
                currency_code="USD",
            ),
            color_info=ColorInfo(
                color_families=[product["color"]], colors=[product["color"]]
            ),
            images=[
                Image(uri=product["image"]),
            ],
            type_=Product.Type.PRIMARY,
        )

        # Add variants to the primary product
        variants = [
            Product(
                id=f"variant_of_{product['id']}_from_{variant_product['id']}",
                title=variant_product["title"],
                categories=["Accessories > Phone Cases"],
                brands=["TestBrand"],
                price_info=PriceInfo(
                    price=variant_product["price"],
                    original_price=variant_product["original_price"],
                    currency_code="USD",
                ),
                color_info=ColorInfo(
                    color_families=[variant_product["color"]],
                    colors=[variant_product["color"]],
                ),
                images=[
                    Image(uri=variant_product["image"]),
                ],
                type_=Product.Type.VARIANT,
                primary_product_id=product["id"],
            )
            for variant_product in product_details
            if variant_product["id"] != product["id"]
        ]

        products.append(primary_product)
        products.extend(variants)

    return products


# Create the import request
def get_import_products_request(products):
    inline_source = ProductInlineSource(products=products)
    input_config = ProductInputConfig(product_inline_source=inline_source)
    return ImportProductsRequest(parent=default_catalog, input_config=input_config)


# Import products
def import_products():
    client = ProductServiceClient()
    products = prepare_products_with_variants()
    import_request = get_import_products_request(products)

    print("Starting product import...")
    operation = client.import_products(import_request)

    while not operation.done():
        print("Operation in progress...")
        time.sleep(5)

    if operation.metadata:
        print(f"Products successfully imported: {operation.metadata.success_count}")
        print(f"Products failed to import: {operation.metadata.failure_count}")
    else:
        print("Operation completed with no metadata.")


if __name__ == "__main__":
    import_products()
