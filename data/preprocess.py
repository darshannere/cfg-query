"""Preprocess Kaggle Online Retail dataset for Tinybird ingestion."""
import pandas as pd
from pathlib import Path

def preprocess_online_retail(input_path: str, output_path: str, max_rows: int = 1000):
    """
    Load, clean, and sample the Online Retail dataset.

    Args:
        input_path: Path to raw CSV file
        output_path: Path to write preprocessed CSV
        max_rows: Maximum number of rows to include
    """
    # Read the dataset
    df = pd.read_csv(input_path, encoding='latin-1')

    # Rename columns to match schema
    df = df.rename(columns={
        'InvoiceNo': 'order_id',
        'CustomerID': 'customer_id',
        'Description': 'product_name',
        'StockCode': 'category',
        'Quantity': 'quantity',
        'UnitPrice': 'unit_price',
        'InvoiceDate': 'order_date',
        'Country': 'country'
    })

    # Calculate total_amount
    df['total_amount'] = df['quantity'] * df['unit_price']

    # Clean data
    df = df.dropna(subset=['customer_id', 'product_name'])
    df['customer_id'] = df['customer_id'].astype(int).astype(str)
    df['order_id'] = df['order_id'].astype(str)
    df['category'] = df['category'].astype(str)

    # Parse dates (format: MM/DD/YYYY HH:MM)
    df['order_date'] = pd.to_datetime(df['order_date'], format='%m/%d/%Y %H:%M')

    # Sample rows
    df = df.head(max_rows)

    # Select final columns
    columns = [
        'order_id', 'customer_id', 'product_name', 'category',
        'quantity', 'unit_price', 'total_amount', 'order_date', 'country'
    ]
    df = df[columns]

    # Write to CSV
    df.to_csv(output_path, index=False)
    print(f"Preprocessed {len(df)} rows to {output_path}")

if __name__ == "__main__":
    input_file = Path(__file__).parent / "online_retail.csv"
    output_file = Path(__file__).parent / "orders.csv"

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        print("Download from: https://www.kaggle.com/datasets/carrie1/ecommerce-data")
        exit(1)

    preprocess_online_retail(str(input_file), str(output_file))
