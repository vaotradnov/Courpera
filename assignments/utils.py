from __future__ import annotations

from typing import Dict, Any

from django.utils import timezone
from django.db import transaction

from .models import Assignment, QuizQuestion, QuizAnswerChoice, Attempt, Grade, AssignmentType
from .models import Assignment as _AssignmentModel
from courses.models import Course
from django.contrib.auth import get_user_model


def grade_quiz(assignment: Assignment, selected: dict[int, int]) -> dict[str, Any]:
    """Grade a quiz assignment.

    - assignment: the Assignment instance (type must be 'quiz')
    - selected: mapping of question_id -> choice_id chosen by the student

    Returns: { 'total': int, 'correct': int, 'score': float, 'per_question': {qid: bool} }
    """
    assert assignment.type == "quiz", "grade_quiz only supports quiz assignments"
    questions = list(assignment.questions.all())
    total = len(questions)
    correct = 0
    perq: dict[int, bool] = {}
    # Preload correct choices into a dict
    correct_map: dict[int, int] = {}
    for q in questions:
        correct_choice = q.choices.filter(is_correct=True).first()
        if not correct_choice:
            # If not defined, treat as incorrect by default
            perq[q.id] = False
            continue
        correct_map[q.id] = correct_choice.id

    for q in questions:
        chosen = selected.get(q.id)
        ok = chosen is not None and correct_map.get(q.id) == chosen
        perq[q.id] = ok
        if ok:
            correct += 1

    score = round((correct / total) * 100.0, 2) if total else 0.0
    return {"total": total, "correct": correct, "score": score, "per_question": perq}


def quiz_readiness(assignment: Assignment) -> dict[str, Any]:
    """Evaluate whether a quiz is ready for students to take.

    Conditions:
    - At least one question
    - Each question has exactly one correct answer
    - Each question has at least two choices
    Returns: { 'ready': bool, 'issues': [str] }
    """
    assert assignment.type == "quiz"
    issues: list[str] = []
    qs = list(assignment.questions.all())
    if not qs:
        issues.append("Quiz has no questions.")
    for q in qs:
        correct_count = q.choices.filter(is_correct=True).count()
        if correct_count != 1:
            issues.append(f"Question {q.order or q.id}: must have exactly one correct answer.")
        if q.choices.count() < 2:
            issues.append(f"Question {q.order or q.id}: must have at least two answer choices.")
    return {"ready": len(issues) == 0, "issues": issues}


@transaction.atomic
def upsert_grade_for_attempt(attempt: Attempt, *, release: bool = False, override_reason: str | None = None) -> Grade:
    """Create or update the Grade record in response to an attempt.

    Behaviour:
    - Quiz: take the best attempt to date (by marks_awarded). Attempts are auto-released.
    - Paper/Exam: use the latest attempt; release is manual (release=True when teacher releases).
    - When overriding a quiz grade, an override_reason should be provided by the teacher.
    """
    a = attempt.assignment
    student = attempt.student
    # Compute marks_awarded if not set (e.g., quiz submission path)
    if attempt.marks_awarded is None:
        if a.type == AssignmentType.QUIZ:
            # Attempt.score is a percentage out of 100
            try:
                score = float(attempt.score or 0.0)
            except Exception:
                score = 0.0
            attempt.marks_awarded = round((score / 100.0) * float(a.max_marks or 100.0), 2)
        else:
            attempt.marks_awarded = 0.0
        attempt.save(update_fields=["marks_awarded"])  # keep existing timestamps

    # Find or create grade record
    grade, _ = Grade.objects.select_for_update().get_or_create(
        assignment=a,
        course=a.course,
        student=student,
        defaults={
            "attempt": attempt,
            "achieved_marks": attempt.marks_awarded or 0.0,
            "max_marks": a.max_marks or 100.0,
            "released_at": timezone.now() if release else None,
        },
    )

    policy = getattr(a, "attempts_policy", _AssignmentModel.AttemptsPolicy.LATEST)
    if policy == _AssignmentModel.AttemptsPolicy.BEST:
        # Choose best marks across attempts
        current_best = float(grade.achieved_marks or 0.0)
        new_marks = float(attempt.marks_awarded or 0.0)
        if new_marks >= current_best or grade.attempt is None:
            grade.attempt = attempt
            grade.achieved_marks = new_marks
            grade.max_marks = float(a.max_marks or 100.0)
            # Quizzes auto-release
            if a.type == AssignmentType.QUIZ:
                grade.released_at = grade.released_at or timezone.now()
            elif release:
                grade.released_at = timezone.now()
            grade.save(update_fields=["attempt", "achieved_marks", "max_marks", "released_at", "updated_at"])
            # Mark attempt as released for quizzes, or when explicitly released
            if a.type == AssignmentType.QUIZ and not attempt.released:
                attempt.released = True
                attempt.released_at = timezone.now()
                attempt.save(update_fields=["released", "released_at"])
            elif release and not attempt.released:
                attempt.released = True
                attempt.released_at = timezone.now()
                attempt.save(update_fields=["released", "released_at"])
    else:
        # Latest: always use the latest attempt provided to this function
        grade.attempt = attempt
        grade.achieved_marks = float(attempt.marks_awarded or 0.0)
        grade.max_marks = float(a.max_marks or 100.0)
        # Quizzes auto-release; others release when asked
        if a.type == AssignmentType.QUIZ:
            grade.released_at = grade.released_at or timezone.now()
            if not attempt.released:
                attempt.released = True
                attempt.released_at = timezone.now()
                attempt.save(update_fields=["released", "released_at"])
        elif release:
            grade.released_at = timezone.now()
            if not attempt.released:
                attempt.released = True
                attempt.released_at = timezone.now()
                attempt.save(update_fields=["released", "released_at"])
        grade.save(update_fields=["attempt", "achieved_marks", "max_marks", "released_at", "updated_at"])

    return grade


def compute_course_percentage(course: Course, student, *, only_released: bool = False) -> float:
    """Compute a student's percentage in a course from Grade records.

    Only counts published assignments.
    """
    qs = Grade.objects.filter(course=course, student=student, assignment__is_published=True)
    if only_released:
        qs = qs.filter(released_at__isnull=False)
    totals = list(qs.values_list("achieved_marks", "max_marks"))
    if not totals:
        return 0.0
    achieved = sum(float(a or 0.0) for a, _ in totals)
    maximum = sum(float(m or 0.0) for _, m in totals) or 0.0
    if maximum <= 0.0:
        return 0.0
    return round((achieved / maximum) * 100.0, 2)


@transaction.atomic
def recalc_grades_for_assignment(assignment: Assignment) -> None:
    """Recalculate Grade rows for an assignment based on its attempts policy.

    Selects per-student best or latest attempt and updates Grade accordingly.
    Respects release policy: quizzes auto-release; others retain released_at
    unless recomputation happens during an explicit release event elsewhere.
    """
    a = assignment
    policy = getattr(a, "attempts_policy", _AssignmentModel.AttemptsPolicy.LATEST)
    # Build attempts per student
    attempts = list(
        Attempt.objects.filter(assignment=a).select_related("student").order_by("student_id", "submitted_at")
    )
    by_student: dict[int, list[Attempt]] = {}
    for att in attempts:
        by_student.setdefault(att.student_id, []).append(att)
    for student_id, att_list in by_student.items():
        chosen: Attempt | None = None
        if policy == _AssignmentModel.AttemptsPolicy.BEST:
            # pick attempt with highest marks_awarded (compute from score if missing for quizzes)
            best_val = -1.0
            for att in att_list:
                marks = att.marks_awarded
                if marks is None and a.type == AssignmentType.QUIZ:
                    try:
                        marks = round((float(att.score or 0.0) / 100.0) * float(a.max_marks or 100.0), 2)
                    except Exception:
                        marks = 0.0
                val = float(marks or 0.0)
                if val >= best_val:
                    best_val = val
                    chosen = att
        else:
            # latest by submitted_at
            chosen = att_list[-1]

        if not chosen:
            continue
        # Ensure marks_awarded filled for quizzes
        if chosen.marks_awarded is None and a.type == AssignmentType.QUIZ:
            try:
                score = float(chosen.score or 0.0)
            except Exception:
                score = 0.0
            chosen.marks_awarded = round((score / 100.0) * float(a.max_marks or 100.0), 2)
            chosen.save(update_fields=["marks_awarded"])
        # Upsert grade using chosen attempt (no implicit release for non-quiz)
        upsert_grade_for_attempt(chosen, release=(a.type == AssignmentType.QUIZ))
