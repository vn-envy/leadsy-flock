# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from app.brief import classify_url, normalize_brief, split_asset_uris


def test_classify_listing_hosts() -> None:
    assert classify_url("https://share.google/rLF34cfolz9TJA92F") == "googleListing"
    assert classify_url("https://maps.google.com/?cid=1") == "googleListing"
    assert classify_url("https://www.google.com/maps/place/Foo") == "googleListing"
    assert classify_url("https://maps.app.goo.gl/abc") == "googleListing"
    assert classify_url("https://goo.gl/maps/abc") == "googleListing"


def test_classify_website() -> None:
    assert classify_url("https://noya.example/salon") == "website"
    assert classify_url("https://glensbakehouse.com/") == "website"
    assert classify_url("") == "website"


def test_split_asset_uris() -> None:
    assert split_asset_uris("https://a.example/x.jpg, https://b.example/y.pdf") == [
        "https://a.example/x.jpg",
        "https://b.example/y.pdf",
    ]
    assert split_asset_uris("not-a-url\nhttps://ok.example/") == ["https://ok.example/"]
    assert split_asset_uris(["https://a.example/1", {"uri": "https://b.example/2"}]) == [
        "https://a.example/1",
        "https://b.example/2",
    ]
    assert split_asset_uris("") == []


def test_normalize_url_listing() -> None:
    out = normalize_brief({"url": "https://share.google/abc"})
    assert out["googleListing"] == "https://share.google/abc"
    assert out["businessName"] == "listing"
    assert not out.get("website")


def test_normalize_url_website_keeps_name() -> None:
    out = normalize_brief({"url": "https://noya.example/", "businessName": "Noya"})
    assert out["website"] == "https://noya.example/"
    assert out["businessName"] == "Noya"


def test_normalize_moves_maps_website_field() -> None:
    out = normalize_brief({"website": "https://maps.app.goo.gl/xyz"})
    assert out["googleListing"] == "https://maps.app.goo.gl/xyz"
    assert not out.get("website")


def test_normalize_asset_split() -> None:
    out = normalize_brief(
        {
            "url": "https://shop.example/",
            "assetUris": "https://shop.example/menu.pdf\nhttps://shop.example/hero.jpg",
        }
    )
    assert out["assetUris"] == [
        "https://shop.example/menu.pdf",
        "https://shop.example/hero.jpg",
    ]
