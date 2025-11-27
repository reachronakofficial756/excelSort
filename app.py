import os
from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd
from flask import Flask, abort, redirect, render_template, request, url_for


SDR_PATH = "SDR_FILE_CLEANED.xlsx"
ZOMATO_PATH = "Zomato_File.xlsx"

# Column names in your Excel files
SDR_MOBILE_COL = "MOBILE NO"
SDR_FIRST_NAME_COL = "FIRST NAME"
SDR_PRESENT_ADDRESS_COL = "PRESENT ADDRESS"
SDR_PERMANENT_ADDRESS_COL = "PERMANENT ADDRESS"
SDR_ALT_NUMBER_COL = "ALTERNATE\nNUMBER"

Z_PHONE_COL = "user_phone_number"
Z_NAME_COL = "user_name"
Z_ORDER_VALUE_COL = "order_value"
Z_ORDER_TIME_COL = "order_time"
Z_RESTAURANT_COL = "restaurant_name"
Z_DELIVERY_ADDR_COL = "delivery_address"
Z_CITY_COL = "city_name"
Z_LAT_COL = "user_saved_latitude"
Z_LON_COL = "user_saved_longitude"


def normalize_mobile_series(series: pd.Series, is_sdr: bool = False) -> pd.Series:
    """Convert possible phone numbers to a clean numeric-only string without leading zeros."""
    import re
    
    def norm(val):
        if pd.isna(val):
            return ''
        try:
            s = str(int(float(val)))
        except:
            s = re.sub(r'\D', '', str(val))
        
        if is_sdr:
            # Remove leading 91 and keep first 10 digits
            if s.startswith('91') and len(s) >= 12:
                s = s[2:]
            s = s[:10]
        
        return s.lstrip('0')
    
    return series.apply(norm)


def normalize_single_mobile(raw: str) -> str:
    """Normalize a single mobile number for search matching."""
    import re
    try:
        s = str(int(float(raw)))
    except:
        s = re.sub(r'\D', '', str(raw))
    
    # Remove leading 91 if present and long enough
    if s.startswith('91') and len(s) >= 12:
        s = s[2:]
    
    # Keep first 10 digits
    s = s[:10]
    return s.lstrip('0')


def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    if not os.path.exists(SDR_PATH) or not os.path.exists(ZOMATO_PATH):
        raise FileNotFoundError("Excel files not found in the project folder.")

    sdr_df = pd.read_excel(SDR_PATH)
    zomato_df = pd.read_excel(ZOMATO_PATH)

    sdr_mobiles = normalize_mobile_series(sdr_df[SDR_MOBILE_COL], is_sdr=True)
    zomato_mobiles = normalize_mobile_series(zomato_df[Z_PHONE_COL], is_sdr=False)

    # Add normalized columns (not strictly needed for template, but useful)
    sdr_df = sdr_df.copy()
    sdr_df["__mobile_norm__"] = sdr_mobiles

    zomato_df = zomato_df.copy()
    zomato_df["__mobile_norm__"] = zomato_mobiles

    # Get intersection of SDR and Zomato
    sdr_set = set(sdr_mobiles[sdr_mobiles != ''])
    zom_set = set(zomato_mobiles[zomato_mobiles != ''])
    intersection = sdr_set & zom_set
    
    # Get SDR numbers without Zomato history
    sdr_only = sdr_set - zom_set
    
    # Combine: first all numbers with Zomato history, then SDR-only numbers
    all_numbers = sorted(list(intersection)) + sorted(list(sdr_only))

    return sdr_df, zomato_df, all_numbers


@dataclass
class SDRRow:
    index: int
    name: str
    present_address: str
    permanent_address: str
    alt_number: str


@dataclass
class OrderRow:
    index: int
    customer_name: str
    restaurant: str
    order_value: float
    order_time: str
    delivery_address: str
    lat: float
    lon: float


def build_customer_context(mobile_norm: str):
    """Prepare all data passed to the HTML template for a single customer."""
    sdr_matches = SDR_DF[SDR_DF["__mobile_norm__"] == mobile_norm]
    zomato_matches = ZOMATO_DF[ZOMATO_DF["__mobile_norm__"] == mobile_norm]

    sdr_rows: List[SDRRow] = []
    for i, row in sdr_matches.iterrows():
        sdr_rows.append(
            SDRRow(
                index=i,
                name=str(row.get(SDR_FIRST_NAME_COL, '')),
                present_address=str(row.get(SDR_PRESENT_ADDRESS_COL, '')),
                permanent_address=str(row.get(SDR_PERMANENT_ADDRESS_COL, '')),
                alt_number=str(row.get(SDR_ALT_NUMBER_COL, '')),
            )
        )

    orders: List[OrderRow] = []
    for i, row in zomato_matches.iterrows():
        # order value might be numeric or string
        try:
            value = float(row.get(Z_ORDER_VALUE_COL, 0))
        except Exception:
            try:
                value = float(str(row.get(Z_ORDER_VALUE_COL, '')).replace("₹", "").strip())
            except Exception:
                value = 0.0

        orders.append(
            OrderRow(
                index=i,
                customer_name=str(row.get(Z_NAME_COL, '')),
                restaurant=str(row.get(Z_RESTAURANT_COL, '')),
                order_value=value,
                order_time=str(row.get(Z_ORDER_TIME_COL, '')),
                delivery_address=str(row.get(Z_DELIVERY_ADDR_COL, '')),
                lat=float(row.get(Z_LAT_COL, 0.0))
                if pd.notna(row.get(Z_LAT_COL))
                else 0.0,
                lon=float(row.get(Z_LON_COL, 0.0))
                if pd.notna(row.get(Z_LON_COL))
                else 0.0,
            )
        )

    total_orders = len(orders)
    avg_order_value = round(sum(o.order_value for o in orders) / total_orders, 2) if total_orders else 0

    primary_city = None
    if not zomato_matches.empty and Z_CITY_COL in zomato_matches.columns:
        primary_city = (
            zomato_matches[Z_CITY_COL].astype(str).value_counts().idxmax()
        )

    # Use first non-empty name from SDR or Zomato
    name = None
    if sdr_rows:
        name = sdr_rows[0].name
    elif orders:
        name = orders[0].customer_name

    return {
        "mobile_display": mobile_norm,
        "mobile_with_country": f"+91{mobile_norm}" if len(mobile_norm) == 10 else mobile_norm,
        "customer_name": name,
        "sdr_rows": sdr_rows,
        "orders": orders,
        "total_orders": total_orders,
        "avg_order_value": avg_order_value,
        "primary_city": primary_city,
        "is_active": total_orders > 0,
    }


app = Flask(__name__)

try:
    SDR_DF, ZOMATO_DF, ALL_MOBILES = load_data()
except Exception as exc:  # pragma: no cover - runtime error path
    SDR_DF, ZOMATO_DF, ALL_MOBILES = pd.DataFrame(), pd.DataFrame(), []
    print(f"Error loading Excel data: {exc}")


@app.route("/")
def index():
    """Serve the landing page."""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        # Fallback: redirect to first customer page if static file not found
        if not ALL_MOBILES:
            abort(500, description="No matching mobile numbers found in both datasets.")
        return redirect(url_for('customer_page', page=1))


@app.route("/search", methods=["POST"])
def search():
    """Find the page for a given mobile number and redirect to it."""
    if not ALL_MOBILES:
        abort(500, description="No matching mobile numbers found in both datasets.")

    mobile_raw = request.form.get("mobile", "").strip()
    if not mobile_raw:
        return redirect(url_for("index"))

    mobile_norm = normalize_single_mobile(mobile_raw)

    try:
        page_index = ALL_MOBILES.index(mobile_norm)
    except ValueError:
        # Number not found – go back to first page with a query param flag
        return redirect(url_for("customer_page", page=1, not_found="1"))

    return redirect(url_for("customer_page", page=page_index + 1))


@app.route("/customer/<int:page>")
def customer_page(page: int):
    if not ALL_MOBILES:
        abort(500, description="No matching mobile numbers found in both datasets.")

    total_pages = len(ALL_MOBILES)
    if page < 1 or page > total_pages:
        abort(404)

    mobile_norm = ALL_MOBILES[page - 1]
    ctx = build_customer_context(mobile_norm)

    # Simple pagination range (1..N). For long lists we could make this smarter.
    page_numbers = list(range(1, total_pages + 1))

    return render_template(
        "customer.html",
        current_page=page,
        total_pages=total_pages,
        page_numbers=page_numbers,
        **ctx,
    )


if __name__ == "__main__":
    app.run(debug=True)
