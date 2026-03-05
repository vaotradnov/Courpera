from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from assignments.models import Assignment, AssignmentType, Attempt, QuizAnswerChoice, QuizQuestion
from courses.models import Course, Enrolment


def make_teacher(username="teacher"):
    u = User.objects.create_user(
        username=username, password="Strong#Passw0rd", email=f"{username}@ex.com"
    )
    prof = u.profile
    prof.role = Role.TEACHER
    prof.save(update_fields=["role"])
    return u


def make_student(username="student"):
    return User.objects.create_user(
        username=username, password="Strong#Passw0rd", email=f"{username}@ex.com"
    )


def make_ready_quiz(course, title="Quiz 1"):
    a = Assignment.objects.create(
        course=course, type=AssignmentType.QUIZ, title=title, attempts_allowed=2
    )
    q = QuizQuestion.objects.create(assignment=a, order=1, text="2+2=?")
    QuizAnswerChoice.objects.create(question=q, order=1, text="3", is_correct=False)
    c2 = QuizAnswerChoice.objects.create(question=q, order=2, text="4", is_correct=True)
    return a, q, c2


@pytest.mark.django_db
def test_quiz_publish_sets_defaults_when_ready(client):
    teacher = make_teacher()
    course = Course.objects.create(owner=teacher, title="C1")
    a, q, correct = make_ready_quiz(course)
    client.force_login(teacher)
    url = reverse("assignments:quiz-manage", args=[a.id])
    # Publish
    resp = client.post(url, {"action": "publish"}, follow=True)
    a.refresh_from_db()
    assert a.is_published is True
    assert a.available_from is not None
    assert a.deadline is not None
    assert 6 <= (a.deadline - a.available_from).days <= 8  # approx a week


@pytest.mark.django_db
def test_quiz_publish_fails_when_not_ready(client):
    teacher = make_teacher()
    course = Course.objects.create(owner=teacher, title="C1")
    a = Assignment.objects.create(course=course, type=AssignmentType.QUIZ, title="Q")
    client.force_login(teacher)
    url = reverse("assignments:quiz-manage", args=[a.id])
    client.post(url, {"action": "publish"})
    a.refresh_from_db()
    assert a.is_published is False


@pytest.mark.django_db
def test_student_availability_and_attempts_enforced_for_quiz(client):
    teacher = make_teacher()
    student = make_student()
    course = Course.objects.create(owner=teacher, title="C1")
    Enrolment.objects.create(course=course, student=student)
    a, q, correct = make_ready_quiz(course)
    a.is_published = True
    a.available_from = timezone.now() + timedelta(days=1)
    a.attempts_allowed = 1
    a.save()

    client.force_login(student)
    # Before available -> redirect back to listing
    resp = client.get(reverse("assignments:take", args=[a.id]))
    assert resp.status_code in (302, 301)

    # Make available now
    a.available_from = timezone.now() - timedelta(minutes=5)
    a.save(update_fields=["available_from"])
    # Can view
    resp = client.get(reverse("assignments:take", args=[a.id]))
    assert resp.status_code == 200
    # Submit correct answer
    submit_url = reverse("assignments:submit", args=[a.id])
    resp = client.post(submit_url, {f"answer_{q.id}": str(correct.id)})
    assert resp.status_code in (302, 301)
    assert Attempt.objects.filter(assignment=a, student=student).count() == 1
    # No attempts left
    resp = client.get(reverse("assignments:take", args=[a.id]))
    assert resp.status_code in (302, 301)


@pytest.mark.django_db
def test_paper_submission_validates_filetype(client):
    teacher = make_teacher()
    student = make_student()
    course = Course.objects.create(owner=teacher, title="C1")
    Enrolment.objects.create(course=course, student=student)
    a = Assignment.objects.create(
        course=course,
        type=AssignmentType.PAPER,
        title="Paper 1",
        is_published=True,
        available_from=timezone.now(),
    )

    client.force_login(student)
    take_url = reverse("assignments:take", args=[a.id])
    assert client.get(take_url).status_code == 200

    # Accept PDF
    pdf = SimpleUploadedFile("test.pdf", b"%PDF-1.4 test", content_type="application/pdf")
    resp = client.post(reverse("assignments:submit", args=[a.id]), {"submission_file": pdf})
    assert resp.status_code in (302, 301)
    assert Attempt.objects.filter(assignment=a, student=student).count() == 1

    # Reject plain text
    a.attempts_allowed = 3
    a.save(update_fields=["attempts_allowed"])
    bad = SimpleUploadedFile("bad.txt", b"hello", content_type="text/plain")
    resp = client.post(
        reverse("assignments:submit", args=[a.id]), {"submission_file": bad}, follow=True
    )
    # No new attempt created
    assert Attempt.objects.filter(assignment=a, student=student).count() == 1


@pytest.mark.django_db
def test_deadline_delta_set_from_available(client):
    teacher = make_teacher()
    course = Course.objects.create(owner=teacher, title="C1")
    a = Assignment.objects.create(course=course, type=AssignmentType.EXAM, title="Exam 1")
    client.force_login(teacher)
    manage = reverse("assignments:manage", args=[a.id])
    base = timezone.now() + timedelta(days=2)
    # Post form including available_from and a chosen delta
    post = {
        "available_from": base.strftime("%Y-%m-%dT%H:%M"),
        "deadline_delta": "1w",
        "action": "set_deadline_delta",
        "title": a.title,
        "attempts_allowed": 2,
    }
    client.post(manage, post)
    a.refresh_from_db()
    assert a.deadline is not None
    # ~ 7 days after provided base
    assert 6 <= (a.deadline - base).days <= 8


@pytest.mark.django_db
def test_attempts_cannot_be_lowered_below_used(client):
    teacher = make_teacher()
    student = make_student()
    course = Course.objects.create(owner=teacher, title="C1")
    Enrolment.objects.create(course=course, student=student)
    a, q, correct = make_ready_quiz(course)
    a.attempts_allowed = 2
    a.is_published = True
    a.available_from = timezone.now()
    a.save()
    # Student makes one attempt
    Attempt.objects.create(
        assignment=a, student=student, attempt_no=1, submitted_at=timezone.now(), score=0
    )
    client.force_login(teacher)
    # Try to lower to 0 (invalid) via quiz manage meta update
    url = reverse("assignments:quiz-manage", args=[a.id])
    payload = {
        "action": "update_meta",
        "title": a.title,
        "available_from": (a.available_from.strftime("%Y-%m-%dT%H:%M") if a.available_from else ""),
        "deadline": "",
        "attempts_allowed": 0,
    }
    resp = client.post(url, payload)
    a.refresh_from_db()
    assert a.attempts_allowed == 2
    # Lower to 1 (equal to used) should be allowed (we only block lower than used)
    payload["attempts_allowed"] = 1
    client.post(url, payload)
    a.refresh_from_db()
    assert a.attempts_allowed == 1


@pytest.mark.django_db
def test_create_assignment_requires_min_attempts(client):
    teacher = make_teacher()
    course = Course.objects.create(owner=teacher, title="C1")
    client.force_login(teacher)
    url = reverse("assignments:create", args=[course.id])
    resp = client.post(
        url,
        {
            "type": AssignmentType.PAPER,
            "title": "P1",
            "instructions": "",
            "attempts_allowed": 0,
        },
    )
    # Expect form re-render (200) with an error message
    assert resp.status_code == 200
    assert b"Attempts must be at least 1" in resp.content
