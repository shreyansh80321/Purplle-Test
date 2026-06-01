from sqlalchemy.orm import Session
from app.db.models import StoreEvent


def get_store_funnel(db: Session, store_id: str = "brigade_bangalore"):
    events = db.query(StoreEvent).filter(StoreEvent.store_id == store_id).all()

    entered = set()
    product_zone = set()
    billing_zone = set()

    for event in events:
        if event.event_type == "entry":
            entered.add(event.track_id)
        elif event.event_type == "zone_visit":
            product_zone.add(event.track_id)
        elif event.event_type == "billing_visit":
            billing_zone.add(event.track_id)

    entered_count = len(entered)
    product_count = len(product_zone)
    billing_count = len(billing_zone)
    converted_count = billing_count

    return {
        "entered_store": entered_count,
        "visited_product_zone": product_count,
        "visited_billing_zone": billing_count,
        "converted": converted_count,
        "drop_off": {
            "entry_to_product_zone": max(entered_count - product_count, 0),
            "product_zone_to_billing": max(product_count - billing_count, 0),
            "billing_to_conversion": max(billing_count - converted_count, 0)
        }
    }