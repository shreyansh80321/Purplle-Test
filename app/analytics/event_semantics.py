from app.db.models import StoreEvent


REVENUE_ZONE_TYPES = {"billing_queue", "shelf", "makeup_unit"}


def is_non_staff(event: StoreEvent):
    return event.is_staff is not True


def visitor_key(event: StoreEvent):
    return event.id_token or event.track_id


def unique_visitor_ids(events):
    return {visitor_key(event) for event in events if visitor_key(event)}


def is_cash_counter_event(event: StoreEvent):
    zone_match = event.zone_id == "cash_counter" or event.zone == "cash_counter"
    queue_zone = event.zone_type == "billing_queue"
    return zone_match or queue_zone


def is_billing_related(event: StoreEvent):
    return (
        event.event_type in {"billing_visit", "queue_completed"}
        or (event.event_type in {"zone_entered", "zone_visit"} and is_cash_counter_event(event))
    )


def is_revenue_zone_event(event: StoreEvent):
    return (
        event.event_type in {"zone_entered", "zone_visit"}
        and (
            event.is_revenue_zone is True
            or event.zone_type in REVENUE_ZONE_TYPES
        )
        and not is_cash_counter_event(event)
    )


def constrain_to_entered(visitor_ids, entered_ids):
    if entered_ids:
        return set(visitor_ids) & set(entered_ids)
    return set()
