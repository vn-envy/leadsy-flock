# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from app.own import collect_uris
from app.vertical import infer_role, infer_vertical, spec


def test_food_vertical_names_the_dish() -> None:
    assert infer_vertical("thali house restaurant in Gurgaon") == "food"
    assert "dish" in spec("food")["proof"].lower() or "menu" in spec("food")["proof"].lower()


def test_dentist_is_clinic_proof() -> None:
    assert infer_vertical("smile dental clinic", category="dentist") == "clinic"


def test_menu_uri_is_proof_role() -> None:
    assert infer_role("https://shop.example/menu.pdf", "menu") == "proof"
    assert infer_role("https://maps.google.com/?cid=1", "maps") == "place"
    assert infer_role("https://glensbakehouse.com/images/cupcake.jpg", "photo") == "proof"


def test_collect_keeps_scout_proof_role() -> None:
    rows = collect_uris(
        {"website": "https://eatery.example/"},
        {
            "ownUris": [
                {
                    "uri": "https://cdn.example/paneer.jpg",
                    "kind": "photo",
                    "role": "proof",
                    "title": "paneer tikka",
                }
            ]
        },
    )
    proof = [r for r in rows if r["uri"].endswith("paneer.jpg")]
    assert proof and proof[0]["role"] == "proof"
