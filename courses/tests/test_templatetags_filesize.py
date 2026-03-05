from __future__ import annotations

from assignments.templatetags.assign_utils import filesize as assign_filesize
from courses.templatetags.course_utils import filesize as course_filesize


def test_filesize_filters_consistent():
    assert assign_filesize(0) == "0 B" and course_filesize(0) == "0 B"
    assert assign_filesize(1024) == "1.0 KB" and course_filesize(1024) == "1.0 KB"
    assert assign_filesize(1536) == "1.5 KB" and course_filesize(1536) == "1.5 KB"
