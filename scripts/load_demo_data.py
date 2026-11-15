"""Load clearly labelled synthetic demonstration records for AgriCare screenshots.

These records are illustrative only. They are NOT official Agmarknet prices,
not live market quotations, and not a real farmer's financial history.
Run from the project root: python scripts/load_demo_data.py
"""
from datetime import datetime, timezone
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import analytics, auth

DEMO_EMAIL = "demo@agricare.local"
DEMO_PASSWORD = "AgriCareDemo@2026"
DEMO_SOURCE = "AgriCare AI demonstration dataset (synthetic; not official/live)"


def main():
    auth.init_auth()
    user = auth.login(DEMO_EMAIL, DEMO_PASSWORD)
    if not user:
        try:
            user = auth.register("AgriCare Demo Farmer", DEMO_EMAIL, DEMO_PASSWORD)
        except ValueError:
            user = auth.login(DEMO_EMAIL, DEMO_PASSWORD)
    if not user:
        raise SystemExit("Could not create or sign in to the demo account.")

    owner = user["farmer_id"]
    # Replace only this demo account's own sample records; never touch other users.
    analytics.init_db()
    with analytics._connect() as db:
        db.execute("DELETE FROM farm_transactions WHERE owner_id=? AND notes LIKE 'AGRICARE_DEMO:%'", (owner,))
        db.execute("DELETE FROM farm_crops WHERE owner_id=? AND notes LIKE 'AGRICARE_DEMO:%'", (owner,))

    transactions = [
        # FY 2026-27 sample entries make the default current-year Analytics view populated.
        ("2026-01-18", "revenue", "Rice", "Crop sale", 68500, 25, "Rabi", "Telangana", "Nalgonda", "AGRICARE_DEMO: illustrative rice sale"),
        ("2026-01-06", "expense", "Rice", "Seeds", 6200, None, "Rabi", "Telangana", "Nalgonda", "AGRICARE_DEMO: illustrative seed cost"),
        ("2026-02-14", "expense", "Rice", "Fertilizers", 8900, None, "Rabi", "Telangana", "Nalgonda", "AGRICARE_DEMO: illustrative fertilizer cost"),
        ("2026-03-22", "revenue", "Maize", "Crop sale", 54200, 20, "Rabi", "Telangana", "Warangal", "AGRICARE_DEMO: illustrative maize sale"),
        ("2026-03-04", "expense", "Maize", "Labour", 7800, None, "Rabi", "Telangana", "Warangal", "AGRICARE_DEMO: illustrative labour cost"),
        ("2026-04-19", "revenue", "Tomato", "Crop sale", 93600, 18, "Zaid", "Telangana", "Ranga Reddy", "AGRICARE_DEMO: illustrative tomato sale"),
        ("2026-04-07", "expense", "Tomato", "Pesticides", 5400, None, "Zaid", "Telangana", "Ranga Reddy", "AGRICARE_DEMO: illustrative pest-control cost"),
        ("2026-05-21", "expense", "Tomato", "Irrigation", 4600, None, "Zaid", "Telangana", "Ranga Reddy", "AGRICARE_DEMO: illustrative irrigation cost"),
        ("2026-06-16", "revenue", "Cotton", "Crop sale", 112000, 28, "Kharif", "Telangana", "Adilabad", "AGRICARE_DEMO: illustrative cotton sale"),
        ("2026-06-03", "expense", "Cotton", "Seeds", 7200, None, "Kharif", "Telangana", "Adilabad", "AGRICARE_DEMO: illustrative seed cost"),
        ("2026-07-12", "expense", "Cotton", "Fertilizers", 10500, None, "Kharif", "Telangana", "Adilabad", "AGRICARE_DEMO: illustrative fertilizer cost"),
        ("2026-08-24", "revenue", "Rice", "Crop sale", 74800, 27, "Kharif", "Telangana", "Nalgonda", "AGRICARE_DEMO: illustrative rice sale"),
        ("2026-08-08", "expense", "Rice", "Labour", 9100, None, "Kharif", "Telangana", "Nalgonda", "AGRICARE_DEMO: illustrative labour cost"),
        ("2026-09-15", "expense", "Cotton", "Transportation", 3800, None, "Kharif", "Telangana", "Adilabad", "AGRICARE_DEMO: illustrative transport cost"),
        ("2026-10-20", "revenue", "Maize", "Crop sale", 61800, 23, "Kharif", "Telangana", "Warangal", "AGRICARE_DEMO: illustrative maize sale"),
        ("2026-10-05", "expense", "Maize", "Electricity", 3200, None, "Kharif", "Telangana", "Warangal", "AGRICARE_DEMO: illustrative electricity cost"),
        ("2026-11-04", "expense", "Tomato", "Labour", 6800, None, "Rabi", "Telangana", "Ranga Reddy", "AGRICARE_DEMO: illustrative labour cost"),
    ]
    for date, kind, crop, category, amount, qty, season, state, district, notes in transactions:
        analytics.add_transaction({"transaction_type": kind, "crop": crop, "category": category,
            "amount_inr": amount, "quantity_quintals": qty, "season": season, "state": state,
            "district": district, "transaction_date": date, "notes": notes}, owner)

    crops = [
        ("Rice", 2.5, "Kharif", "2026-06-10", "2026-10-24", 6200, 2780, "Telangana", "Nalgonda"),
        ("Maize", 2.0, "Kharif", "2026-06-18", "2026-10-16", 4600, 2680, "Telangana", "Warangal"),
        ("Cotton", 3.0, "Kharif", "2026-06-05", "2026-11-01", 5100, 7100, "Telangana", "Adilabad"),
        ("Tomato", 1.2, "Rabi", "2026-10-12", "2027-01-20", 8400, 3200, "Telangana", "Ranga Reddy"),
    ]
    for crop, area, season, sow, harvest, kg, price, state, district in crops:
        analytics.add_crop({"crop": crop, "area_acres": area, "season": season,
            "sowing_date": sow, "harvest_date": harvest, "production_kg": kg,
            "selling_price_inr_per_quintal": price, "price_verified": False,
            "price_source": "", "state": state, "district": district,
            "soil_type": "Red soil", "notes": "AGRICARE_DEMO: illustrative crop record; not actual farm data"}, owner)

    # Monthly-spaced observations provide visible charts without claiming daily/live accuracy.
    market_rows = []
    sample_markets = [
        ("Telangana", "Nalgonda", "Nalgonda", {"Rice": (2200, 2480, 2360), "Maize": (1850, 2180, 2020), "Cotton": (6500, 7200, 6880), "Tomato": (1800, 3200, 2500)}),
        ("Telangana", "Warangal", "Warangal", {"Rice": (2180, 2460, 2320), "Maize": (1900, 2250, 2100), "Cotton": (6600, 7350, 7010), "Tomato": (1700, 3100, 2400)}),
        ("Andhra Pradesh", "Guntur", "Guntur", {"Rice": (2250, 2520, 2410), "Maize": (1880, 2200, 2060), "Cotton": (6550, 7280, 6950), "Chilli": (9000, 14500, 11800)}),
        ("Maharashtra", "Pune", "Pune", {"Onion": (1200, 2600, 1900), "Tomato": (1600, 3400, 2550), "Soybean": (3900, 4600, 4250), "Wheat": (2350, 2750, 2550)}),
    ]
    for month in range(4, 13):
        year = 2025
        for state, district, market, commodities in sample_markets:
            for commodity, (low, high, modal) in commodities.items():
                # Small deterministic monthly variation, explicitly illustrative.
                shift = ((month * 37 + len(commodity) * 11) % 9)
                lo, hi, mid = low + shift, high + shift, modal + shift
                market_rows.append({"state": state, "district": district, "market": market,
                    "commodity": commodity, "variety": "FAQ", "grade": "FAQ",
                    "report_date": f"{year}-{month:02d}-15", "min_price": lo,
                    "max_price": hi, "modal_price": mid, "arrivals": 10 + month,
                })
    for month in range(1, 4):
        for state, district, market, commodities in sample_markets:
            for commodity, (low, high, modal) in commodities.items():
                shift = ((month * 29 + len(commodity) * 7) % 9)
                market_rows.append({"state": state, "district": district, "market": market,
                    "commodity": commodity, "variety": "FAQ", "grade": "FAQ",
                    "report_date": f"2026-{month:02d}-15", "min_price": low + shift,
                    "max_price": high + shift, "modal_price": modal + shift,
                    "arrivals": 12 + month})
    imported = analytics.import_mandi_rows(market_rows, DEMO_SOURCE, "daily")
    print("AgriCare demonstration data loaded.")
    print(f"Demo login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print(f"Financial transactions: {len(transactions)}; crop records: {len(crops)}")
    print(f"Mandi sample observations: {imported['imported_or_updated']}")
    print("IMPORTANT: All inserted financial and mandi values are synthetic examples for demonstration only, not actual farmer records or official/live market prices.")



if __name__ == "__main__":
    main()
