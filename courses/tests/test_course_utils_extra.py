from __future__ import annotations

from courses.templatetags.course_utils import filesize


def test_filesize_handles_non_number_input():
    assert filesize("oops") == "0 B"
