from __future__ import annotations

from messaging.consumer_helpers import presence_add, presence_get, presence_remove


def test_presence_helpers_add_get_remove_sets_are_consistent():
    room = 98765
    # Start empty
    assert presence_get(room) == set()
    # Add two users
    s1 = presence_add(room, 1)
    s2 = presence_add(room, 2)
    assert s1 == {1} or s1 == {1}  # first add returns a set with user 1
    assert s2 == {1, 2}
    # Remove one, then the other
    s3 = presence_remove(room, 1)
    assert s3 == {2}
    s4 = presence_remove(room, 2)
    assert s4 == set()
