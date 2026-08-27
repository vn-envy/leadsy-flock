# Copyright 2026 Neekhil Vatsa
# Licensed under the Apache License, Version 2.0

from app.flock import FLOCK, describe_flock


def test_flock_has_eight_birds() -> None:
    assert len(FLOCK) == 8
    ids = {bird.id for bird in FLOCK}
    assert ids == {
        "flo",
        "bri",
        "scout",
        "inka",
        "stella",
        "ray",
        "callie",
        "ledge",
    }


def test_always_on_birds_are_free_core() -> None:
    always = {bird.id for bird in FLOCK if bird.always_on}
    assert always == {"flo", "bri", "ledge"}


def test_callie_is_listed_but_not_hired() -> None:
    callie = next(bird for bird in FLOCK if bird.id == "callie")
    assert callie.hired_in_hackathon_run is False


def test_describe_flock_mentions_director() -> None:
    text = describe_flock()
    assert "Flo" in text
    assert "Director" in text
