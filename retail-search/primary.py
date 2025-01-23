# Import products into a catalog as primary products using Retail API
import random
import string
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
from google.protobuf.field_mask_pb2 import FieldMask

# Fetch the project ID from the Google Cloud authentication setup
project_id = google.auth.default()[1]

# Define the default catalog resource
default_catalog = f"projects/{project_id}/locations/global/catalogs/default_catalog/branches/default_branch"


# Prepare products to import as standalone primary products
def prepare_products_as_primaries():
    products = []

    # Convert original primary to a standalone product
    primary_product = Product(
        id="primary_case_black",
        title="iPhone Case Black",
        categories=["Accessories > Phone Cases"],
        brands=["TestBrand"],
        price_info=PriceInfo(price=25.0, original_price=30.0, currency_code="USD"),
        color_info=ColorInfo(color_families=["Black"], colors=["Black"]),
        images=[
            Image(uri="https://storage.googleapis.com/doit-retail-search/black.png"),
        ],
        type_=Product.Type.PRIMARY,
    )
    products.append(primary_product)

    # Convert variants to standalone primary products
    variant1 = Product(
        id="primary_case_beige",
        title="iPhone Case Beige",
        categories=["Accessories > Phone Cases"],
        brands=["TestBrand"],
        price_info=PriceInfo(price=26.0, original_price=32.0, currency_code="USD"),
        color_info=ColorInfo(color_families=["Beige"], colors=["Beige"]),
        images=[
            Image(uri="https://storage.googleapis.com/doit-retail-search/beige.png"),
        ],
        type_=Product.Type.PRIMARY,  # Changed type to PRIMARY
    )
    products.append(variant1)

    variant2 = Product(
        id="primary_case_yellow",
        title="iPhone Case Yellow",
        categories=["Accessories > Phone Cases"],
        brands=["TestBrand"],
        price_info=PriceInfo(price=27.0, original_price=34.0, currency_code="USD"),
        color_info=ColorInfo(color_families=["Yellow"], colors=["Yellow"]),
        images=[
            Image(uri="https://storage.googleapis.com/doit-retail-search/yellow.png"),
        ],
        type_=Product.Type.PRIMARY,  # Changed type to PRIMARY
    )
    products.append(variant2)

    return products


# Create the import request
def get_import_products_request(products):
    inline_source = ProductInlineSource(products=products)
    input_config = ProductInputConfig(product_inline_source=inline_source)
    return ImportProductsRequest(parent=default_catalog, input_config=input_config)


# Import products
def import_products():
    client = ProductServiceClient()
    products = prepare_products_as_primaries()
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
