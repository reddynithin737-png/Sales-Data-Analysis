import os
import pandas as pd
from datetime import datetime
import database

REQUIRED_COLUMNS = [
    'sale_id', 'product_id', 'product_name', 'category',
    'sale_date', 'quantity', 'unit_price', 'customer', 'region'
]

def validate_sales_csv(file_path):
    """
    Validates an uploaded CSV file according to specifications.
    Returns:
        report = {
            'is_structure_valid': True/False,
            'structure_error': str,
            'total_rows': int,
            'valid_count': int,
            'invalid_count': int,
            'duplicate_count': int,
            'valid_rows': list of dicts,
            'invalid_rows': list of dicts with 'row_num', 'sale_id', 'data', 'reason',
            'duplicate_rows': list of dicts with 'row_num', 'sale_id', 'data', 'reason'
        }
    """
    try:
        df = pd.read_csv(file_path, dtype=str)
    except Exception as e:
        return {
            'is_structure_valid': False,
            'structure_error': f"Failed to read CSV file: {str(e)}",
            'total_rows': 0,
            'valid_count': 0,
            'invalid_count': 0,
            'duplicate_count': 0,
            'valid_rows': [],
            'invalid_rows': [],
            'duplicate_rows': []
        }

    # Normalize column names: strip whitespace and lowercase
    raw_columns = [c.strip() for c in df.columns]
    df.columns = raw_columns
    col_map = {c.lower(): c for c in raw_columns}

    # Check for required columns
    missing_columns = [col for col in REQUIRED_COLUMNS if col.lower() not in col_map]
    if missing_columns:
        return {
            'is_structure_valid': False,
            'structure_error': f"Missing required columns: {', '.join(missing_columns)}. Required: {', '.join(REQUIRED_COLUMNS)}",
            'total_rows': len(df),
            'valid_count': 0,
            'invalid_count': len(df),
            'duplicate_count': 0,
            'valid_rows': [],
            'invalid_rows': [],
            'duplicate_rows': []
        }

    # Standardize column casing
    renamed_df = pd.DataFrame()
    for col in REQUIRED_COLUMNS:
        renamed_df[col] = df[col_map[col.lower()]]

    # Get set of existing sale_ids from database for fast duplicate lookup
    existing_sales = database.execute_query("SELECT sale_id FROM sales", fetchall=True)
    existing_sale_ids = set()
    if existing_sales:
        for r in existing_sales:
            if r.get('sale_id') is not None:
                existing_sale_ids.add(str(r['sale_id']).strip())

    seen_in_file_sale_ids = set()
    valid_rows = []
    invalid_rows = []
    duplicate_rows = []

    for idx, row in renamed_df.iterrows():
        row_num = idx + 2  # 1-indexed, accounting for header line
        reasons = []

        # Extract values
        sale_id = str(row['sale_id']).strip() if pd.notna(row['sale_id']) else ''
        prod_id = str(row['product_id']).strip() if pd.notna(row['product_id']) else ''
        product_name = str(row['product_name']).strip() if pd.notna(row['product_name']) else ''
        category = str(row['category']).strip() if pd.notna(row['category']) else ''
        sale_date = str(row['sale_date']).strip() if pd.notna(row['sale_date']) else ''
        quantity_str = str(row['quantity']).strip() if pd.notna(row['quantity']) else ''
        unit_price_str = str(row['unit_price']).strip() if pd.notna(row['unit_price']) else ''
        customer = str(row['customer']).strip() if pd.notna(row['customer']) else ''
        region = str(row['region']).strip() if pd.notna(row['region']) else ''

        row_data = {
            'sale_id': sale_id,
            'product_id': prod_id,
            'product_name': product_name,
            'category': category,
            'sale_date': sale_date,
            'quantity': quantity_str,
            'unit_price': unit_price_str,
            'customer': customer,
            'region': region
        }

        # 1. Check required non-empty fields
        if not product_name:
            reasons.append("Product name is required.")
        if not category:
            reasons.append("Category is required.")
        if not customer:
            reasons.append("Customer name is required.")
        if not region:
            reasons.append("Region is required.")
        if not sale_date:
            reasons.append("Sale date is required.")

        # 2. Validate Date format
        parsed_date = None
        if sale_date:
            date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(sale_date, fmt).strftime('%Y-%m-%d')
                    break
                except ValueError:
                    pass
            if not parsed_date:
                reasons.append(f"Invalid date format '{sale_date}'. Expected YYYY-MM-DD.")
            else:
                row_data['sale_date'] = parsed_date

        # 3. Validate Quantity
        valid_qty = None
        try:
            valid_qty = int(float(quantity_str))
            if valid_qty <= 0:
                reasons.append(f"Quantity must be greater than 0 (got {quantity_str}).")
            else:
                row_data['quantity'] = valid_qty
        except (ValueError, TypeError):
            reasons.append(f"Quantity must be a valid integer (got '{quantity_str}').")

        # 4. Validate Unit Price
        valid_price = None
        try:
            valid_price = float(unit_price_str)
            if valid_price < 0:
                reasons.append(f"Unit price cannot be negative (got {unit_price_str}).")
            else:
                row_data['unit_price'] = round(valid_price, 2)
        except (ValueError, TypeError):
            reasons.append(f"Unit price must be a valid number (got '{unit_price_str}').")

        # Calculate revenue for preview if quantity and price are valid
        if valid_qty is not None and valid_price is not None and valid_qty > 0 and valid_price >= 0:
            row_data['revenue'] = round(valid_qty * valid_price, 2)
        else:
            row_data['revenue'] = 0.0

        # If there are data validity errors, mark as invalid
        if reasons:
            invalid_rows.append({
                'row_num': row_num,
                'sale_id': sale_id or 'N/A',
                'data': row_data,
                'reason': " | ".join(reasons)
            })
            continue

        # 5. Check Duplicate Policy
        # Check within-file duplicate
        if sale_id:
            if sale_id in seen_in_file_sale_ids:
                duplicate_rows.append({
                    'row_num': row_num,
                    'sale_id': sale_id,
                    'data': row_data,
                    'reason': f"Duplicate sale_id '{sale_id}' repeated multiple times in this CSV file."
                })
                continue
            elif sale_id in existing_sale_ids:
                duplicate_rows.append({
                    'row_num': row_num,
                    'sale_id': sale_id,
                    'data': row_data,
                    'reason': f"Sale ID '{sale_id}' already exists in database (Policy: skipped to prevent duplicate)."
                })
                continue
            else:
                seen_in_file_sale_ids.add(sale_id)

        # Record is valid!
        valid_rows.append({
            'row_num': row_num,
            'sale_id': sale_id,
            'data': row_data
        })

    return {
        'is_structure_valid': True,
        'structure_error': None,
        'total_rows': len(renamed_df),
        'valid_count': len(valid_rows),
        'invalid_count': len(invalid_rows),
        'duplicate_count': len(duplicate_rows),
        'valid_rows': valid_rows,
        'invalid_rows': invalid_rows,
        'duplicate_rows': duplicate_rows
    }

def import_valid_records(valid_rows, user_id=None):
    """
    Inserts valid records into database.
    Creates or matches product and registers sale.
    Returns (imported_count, error_count)
    """
    imported_count = 0
    errors = 0

    for item in valid_rows:
        data = item['data']
        try:
            prod_id = database.get_or_create_product(data['product_name'], data['category'])
            sale_id_val = int(data['sale_id']) if data.get('sale_id') and str(data['sale_id']).isdigit() else None
            
            database.insert_sale(
                sale_date=data['sale_date'],
                product_id=prod_id,
                quantity=int(data['quantity']),
                unit_price=float(data['unit_price']),
                customer=data['customer'],
                region=data['region'],
                user_id=user_id,
                sale_id=sale_id_val
            )
            imported_count += 1
        except Exception as e:
            print(f"[Import Error] Failed to insert row {item['row_num']}: {e}")
            errors += 1

    return imported_count, errors
