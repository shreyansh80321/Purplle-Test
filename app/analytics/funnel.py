from sqlalchemy.orm import Session
from app.analytics.event_semantics import (
    constrain_to_entered,
    is_billing_related,
    is_non_staff,
    is_revenue_zone_event,
    unique_visitor_ids,
)
from app.db.models import StoreEvent


def get_store_funnel(db: Session, store_id: str = "brigade_bangalore"):
    events = db.query(StoreEvent).filter(StoreEvent.store_id == store_id).all()

    non_staff_events = [event for event in events if is_non_staff(event)]
    entered = unique_visitor_ids([event for event in non_staff_events if event.event_type == "entry"])
    revenue_zone = constrain_to_entered(
        unique_visitor_ids([event for event in non_staff_events if is_revenue_zone_event(event)]),
        entered,
    )
    queue_or_cash = constrain_to_entered(
        unique_visitor_ids([event for event in non_staff_events if is_billing_related(event)]),
        entered,
    )
    converted = constrain_to_entered(
        unique_visitor_ids([event for event in non_staff_events if event.event_type == "queue_completed"]),
        entered,
    )

    entered_count = len(entered)
    revenue_count = min(len(revenue_zone), entered_count)
    queue_count = min(len(queue_or_cash), revenue_count)
    converted_count = min(len(converted or queue_or_cash), queue_count, entered_count)

    return {
        "entered_store": entered_count,
        "visited_revenue_zone": revenue_count,
        "product_zone": revenue_count,
        "joined_queue_or_visited_cash_counter": queue_count,
        "converted": converted_count,
        "drop_offs": {
            "entry_to_revenue_zone": max(entered_count - revenue_count, 0),
            "revenue_zone_to_queue_or_cash_counter": max(revenue_count - queue_count, 0),
            "queue_or_cash_counter_to_conversion": max(queue_count - converted_count, 0),
        }
    }
