# Data Directory

This directory contains the data files for the E-commerce Analytics Platform.

## Directory Structure

```
data/
├── raw/           # Raw data files from Olist dataset
└── processed/     # Processed and transformed data files
```

## Olist Dataset

Please download the following files from [Olist Dataset on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and place them in the `raw/` directory:

1. olist_customers_dataset.csv
2. olist_orders_dataset.csv
3. olist_order_items_dataset.csv
4. olist_products_dataset.csv
5. olist_sellers_dataset.csv
6. product_category_name_translation.csv

## Data Processing

The raw data files will be automatically processed when you run the application. Processed files will be stored in the `processed/` directory.
