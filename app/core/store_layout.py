from copy import deepcopy


DEFAULT_LAYOUT_DESCRIPTION = (
    "Store layout zones are normalized operational rectangles in camera space. "
    "They are inspired by the assessment layout semantics and are approximate, "
    "not exact CAD or blueprint coordinates."
)


DEFAULT_LAYOUT_ZONES = {
    "entrance": {
        "zone_id": "entrance",
        "zone_name": "Entrance",
        "zone_type": "entrance",
        "is_revenue_zone": False,
        "description": "Customer ingress and egress threshold near the storefront.",
        "rect": [0.0, 0.0, 0.22, 1.0],
    },
    "foh_customer_area": {
        "zone_id": "foh_customer_area",
        "zone_name": "F.O.H Customer Area",
        "zone_type": "customer_area",
        "is_revenue_zone": False,
        "description": "Front-of-house customer browsing and circulation area.",
        "rect": [0.18, 0.12, 0.82, 0.95],
    },
    "boh_staff_area": {
        "zone_id": "boh_staff_area",
        "zone_name": "B.O.H Staff Area",
        "zone_type": "staff_area",
        "is_revenue_zone": False,
        "description": "Back-of-house operational area reserved for staff movement.",
        "rect": [0.0, 0.0, 0.25, 0.28],
    },
    "cash_counter": {
        "zone_id": "cash_counter",
        "zone_name": "Cash Counter",
        "zone_type": "billing_queue",
        "is_revenue_zone": True,
        "description": "Billing desk and queue service area.",
        "rect": [0.72, 0.0, 1.0, 0.45],
    },
    "wall_unit": {
        "zone_id": "wall_unit",
        "zone_name": "Wall Unit / Shelf",
        "zone_type": "shelf",
        "is_revenue_zone": True,
        "description": "Perimeter product shelf or wall merchandising zone.",
        "rect": [0.18, 0.12, 0.38, 0.9],
    },
    "makeup_unit": {
        "zone_id": "makeup_unit",
        "zone_name": "Makeup Unit",
        "zone_type": "makeup_unit",
        "is_revenue_zone": True,
        "description": "Makeup merchandising or trial unit area.",
        "rect": [0.42, 0.2, 0.62, 0.72],
    },
    "product_shelves": {
        "zone_id": "product_shelves",
        "zone_name": "Product / Brand Shelves",
        "zone_type": "shelf",
        "is_revenue_zone": True,
        "description": "General product and brand shelf browsing zone.",
        "rect": [0.62, 0.18, 0.9, 0.9],
    },
    "outside_passby": {
        "zone_id": "outside_passby",
        "zone_name": "Outside Passby",
        "zone_type": "outside_passby",
        "is_revenue_zone": False,
        "description": "External walkway motion outside the customer entry path.",
        "rect": [0.78, 0.0, 1.0, 1.0],
    },
}


def _with_overrides(zone_key: str, rect):
    zone = deepcopy(DEFAULT_LAYOUT_ZONES[zone_key])
    zone["rect"] = rect
    return zone


def build_semantic_layout(camera_role: str):
    response_camera_role = "semantic_layout"
    zones = {
        key: deepcopy(value)
        for key, value in DEFAULT_LAYOUT_ZONES.items()
    }

    if camera_role == "entrance":
        zones["entrance"] = _with_overrides("entrance", [0.0, 0.0, 0.28, 1.0])
        zones["foh_customer_area"] = _with_overrides("foh_customer_area", [0.24, 0.12, 0.84, 0.95])
        zones["cash_counter"] = _with_overrides("cash_counter", [0.74, 0.0, 1.0, 0.4])
        zones["outside_passby"] = _with_overrides("outside_passby", [0.0, 0.0, 0.14, 1.0])
        zones["boh_staff_area"] = _with_overrides("boh_staff_area", [0.0, 0.0, 0.18, 0.25])
    elif camera_role == "inside_store":
        zones["entrance"] = _with_overrides("entrance", [0.0, 0.0, 0.16, 0.28])
        zones["outside_passby"] = _with_overrides("outside_passby", [0.92, 0.0, 1.0, 0.2])
    elif camera_role == "outside_passby":
        zones["outside_passby"] = _with_overrides("outside_passby", [0.32, 0.0, 1.0, 1.0])
        zones["entrance"] = _with_overrides("entrance", [0.0, 0.0, 0.26, 1.0])
        zones["foh_customer_area"] = _with_overrides("foh_customer_area", [0.0, 0.0, 0.22, 1.0])
        zones["boh_staff_area"] = _with_overrides("boh_staff_area", [0.0, 0.0, 0.12, 0.22])

    return {
        "camera_role": response_camera_role,
        "description": DEFAULT_LAYOUT_DESCRIPTION,
        "zones": list(zones.values()),
    }


def get_zone_by_point(camera_role: str, nx: float, ny: float):
    layout = build_semantic_layout(camera_role)

    for zone in layout["zones"]:
        x1, y1, x2, y2 = zone["rect"]
        if x1 <= nx <= x2 and y1 <= ny <= y2:
            return zone

    return {
        "zone_id": "unknown",
        "zone_name": "Unknown",
        "zone_type": "unknown",
        "is_revenue_zone": False,
        "description": "Point does not fall into a configured semantic zone.",
        "rect": None,
    }
