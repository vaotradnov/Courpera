from __future__ import annotations

import csv
import random
import re
from pathlib import Path
from typing import Iterable

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Role, UserProfile
from courses.models import Course, Enrolment

FIRST_NAMES = [
    "Olivia",
    "Noah",
    "Amelia",
    "Liam",
    "Isla",
    "Oliver",
    "Ava",
    "Elijah",
    "Mia",
    "Mateo",
    "Sophia",
    "Lucas",
    "Charlotte",
    "Levi",
    "Harper",
    "James",
    "Evelyn",
    "Benjamin",
    "Luna",
    "Ethan",
    "Aria",
    "Sebastian",
    "Scarlett",
    "Jack",
    "Mila",
    "Henry",
    "Layla",
    "Aiden",
    "Ellie",
    "Wyatt",
    "Nora",
    "Carter",
    "Hazel",
    "Daniel",
    "Zoey",
    "Owen",
    "Lily",
    "Leo",
    "Aurora",
    "Jackson",
    "Violet",
    "Gabriel",
    "Penelope",
    "Grayson",
    "Gianna",
    "Michael",
    "Chloe",
    "Muhammad",
    "Riley",
    "Alexander",
    "Zoe",
    "Samuel",
    "Elena",
    "David",
    "Aaliyah",
    "Joseph",
    "Lillian",
    "Mason",
    "Hannah",
    "Charles",
    "Addison",
    "Luke",
    "Eleanor",
    "Julian",
    "Paisley",
    "Anthony",
    "Grace",
    "Isaac",
    "Natalie",
    "Dylan",
    "Eliana",
    "Ezra",
    "Savannah",
    "Thomas",
    "Brooklyn",
    "Hudson",
    "Leah",
    "Caleb",
    "Aubrey",
    "Christopher",
    "Stella",
    "Landon",
    "Madison",
    "Nathan",
    "Willow",
    "Hunter",
    "Lucy",
    "Elias",
    "Paislee",
    "Josiah",
]

LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Sanchez",
    "Clark",
    "Ramirez",
    "Lewis",
    "Robinson",
    "Walker",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Scott",
    "Torres",
    "Nguyen",
    "Hill",
    "Flores",
    "Green",
    "Adams",
    "Nelson",
    "Baker",
    "Hall",
    "Rivera",
    "Campbell",
    "Mitchell",
    "Carter",
    "Roberts",
    "Gomez",
    "Phillips",
    "Evans",
    "Turner",
    "Diaz",
    "Parker",
    "Cruz",
    "Edwards",
    "Collins",
    "Reyes",
    "Stewart",
    "Morris",
    "Morales",
    "Murphy",
    "Cook",
    "Rogers",
    "Gutierrez",
    "Ortiz",
    "Morgan",
    "Cooper",
    "Peterson",
    "Bailey",
    "Reed",
    "Kelly",
    "Howard",
    "Ramos",
    "Kim",
    "Cox",
    "Ward",
    "Richardson",
    "Watson",
    "Brooks",
    "Chavez",
    "Wood",
    "James",
    "Bennett",
    "Gray",
    "Mendoza",
    "Ruiz",
    "Hughes",
]

SUBJECTS = [
    "Data Science",
    "Web Development",
    "Algorithms",
    "UX Design",
    "Cloud Computing",
    "Machine Learning",
    "Cybersecurity",
    "Databases",
    "Networks",
    "Mathematics",
    "Physics",
    "Mobile Development",
    "DevOps",
    "Computer Vision",
    "NLP",
    "Distributed Systems",
    "Software Testing",
    "Game Development",
    "AI Ethics",
]

TIMEZONES = [
    "Europe/London",
    "UTC",
    "America/New_York",
    "America/Edmonton",
    "Europe/Berlin",
    "Asia/Kolkata",
    "America/Los_Angeles",
]


def _slugify_name(a: str) -> str:
    s = a.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _username_from(first: str, last: str, taken: set[str]) -> str:
    base = f"{first}.{last}".lower()
    base = re.sub(r"[^a-z0-9.]+", "", base)
    name = base
    i = 1
    while name in taken:
        i += 1
        name = f"{base}{i}"
    taken.add(name)
    return name


def _random_phone(rng: random.Random) -> str:
    # UK-style: 07XXXXXXXXX
    return "07" + "".join(rng.choice("0123456789") for _ in range(9))


def _random_password(rng: random.Random, user: User) -> str:
    # Policy: min length 12, include upper/lower/digit/symbol, avoid similarity to user fields.
    # Generate up to 10 attempts until validation passes.
    alphabet_upper = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # pragma: allowlist secret
    alphabet_lower = "abcdefghjkmnpqrstuvwxyz"  # pragma: allowlist secret
    digits = "23456789"  # pragma: allowlist secret
    symbols = "!@#$%^&*()-_=+[]{}:,.?"  # pragma: allowlist secret
    for _ in range(10):
        parts = [
            rng.choice(alphabet_upper),
            rng.choice(alphabet_lower),
            rng.choice(digits),
            rng.choice(symbols),
        ]
        length = rng.randint(12, 18)
        rest_len = max(0, length - len(parts))
        rest_alpha = alphabet_upper + alphabet_lower + digits + symbols
        parts += [rng.choice(rest_alpha) for _ in range(rest_len)]
        rng.shuffle(parts)
        pwd = "".join(parts)
        # Extra guard: avoid substrings of username or email prefix
        uname = (user.username or "").lower()
        email_local = (user.email or "").split("@")[0].lower()
        if uname and uname in pwd.lower():
            continue
        if email_local and email_local in pwd.lower():
            continue
        try:
            validate_password(pwd, user)
        except Exception:
            continue
        return pwd
    # Fallback (should rarely happen)
    return "Aa1!" + _slugify_name(user.username or "user") + "#2026"


def _unique_codes(rng: random.Random, count: int, min_v: int, max_v: int) -> Iterable[int]:
    # Sample without replacement (range size is >> count)
    return rng.sample(range(min_v, max_v + 1), count)


class Command(BaseCommand):
    help = "Purge and seed demo data (students, instructors, courses, enrolments)."

    def add_arguments(self, parser):  # noqa: D401
        parser.add_argument(
            "--purge", action="store_true", help="Delete existing data before seeding"
        )
        parser.add_argument(
            "--include-superusers",
            action="store_true",
            help="Also delete superusers during purge (use with caution)",
        )
        parser.add_argument("--students", type=int, default=100)
        parser.add_argument("--instructors", type=int, default=10)
        parser.add_argument("--courses", type=int, default=20)
        parser.add_argument("--enrol-min", type=int, default=2)
        parser.add_argument("--enrol-max", type=int, default=5)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument(
            "--dump", type=str, default="", help="Path to write a JSON fixture after seeding"
        )
        parser.add_argument(
            "--export-credentials",
            type=str,
            default="",
            help="Optional CSV path to export plaintext credentials (store securely)",
        )
        parser.add_argument(
            "--create-admin",
            action="store_true",
            help="Create or reset an admin superuser account",
        )
        parser.add_argument(
            "--admin-username",
            type=str,
            default="admin",
            help="Admin username (default: admin)",
        )
        parser.add_argument(
            "--admin-password",
            type=str,
            default="CM3035",
            help="Admin password (default: CM3035)",
        )

    @transaction.atomic
    def handle(self, *args, **options):  # noqa: D401
        rng = random.Random(int(options["seed"]))
        students_n = int(options["students"]) or 0
        instructors_n = int(options["instructors"]) or 0
        courses_n = int(options["courses"]) or 0
        enrol_min = int(options["enrol_min"]) or 2
        enrol_max = int(options["enrol_max"]) or 5
        if enrol_min > enrol_max:
            raise CommandError("--enrol-min cannot be greater than --enrol-max")

        if options["purge"]:
            self.stdout.write(self.style.WARNING("Purging existing data..."))
            Enrolment.objects.all().delete()
            Course.objects.all().delete()
            UserModel = get_user_model()
            qs = UserModel.objects.all()
            if not options["include_superusers"]:
                qs = qs.filter(is_superuser=False)
            # Avoid deleting currently logged-in session user inadvertently; proceed in dev contexts only.
            qs.delete()

        self.stdout.write("Generating users...")
        taken_usernames: set[str] = set()
        UserModel = get_user_model()

        # Instructors first
        instr_codes = list(_unique_codes(rng, instructors_n, 1, 99999))
        instructors: list[User] = []
        creds_rows: list[list[str]] = []
        for i in range(instructors_n):
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            username = _username_from(first, last, taken_usernames)
            email = f"{username}@courpera.com"
            u = UserModel.objects.create_user(username=username, email=email)
            # Promote to teacher role and assign instructor id
            prof: UserProfile = u.profile  # created by signal
            prof.role = Role.TEACHER
            prof.full_name = f"{first} {last}"
            prof.timezone = rng.choice(TIMEZONES)
            prof.phone = _random_phone(rng)
            prof.instructor_id = f"I{instr_codes[i]:05d}"
            prof.save()
            # Set random strong password (validated)
            pwd = _random_password(rng, u)
            u.set_password(pwd)
            u.save(update_fields=["password"])
            instructors.append(u)
            creds_rows.append([u.username, u.email, "teacher", prof.instructor_id or "", pwd])

        # Students
        stud_codes = list(_unique_codes(rng, students_n, 1, 99999))
        students: list[User] = []
        for i in range(students_n):
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            username = _username_from(first, last, taken_usernames)
            email = f"{username}@courpera.com"
            u = UserModel.objects.create_user(username=username, email=email)
            sprof: UserProfile = u.profile
            sprof.role = Role.STUDENT
            sprof.full_name = f"{first} {last}"
            sprof.timezone = rng.choice(TIMEZONES)
            sprof.phone = _random_phone(rng)
            sprof.student_number = f"S{stud_codes[i]:05d}"
            sprof.save()
            pwd = _random_password(rng, u)
            u.set_password(pwd)
            u.save(update_fields=["password"])
            students.append(u)
            creds_rows.append([u.username, u.email, "student", sprof.student_number or "", pwd])

        self.stdout.write("Generating courses...")
        titles: set[str] = set()
        courses: list[Course] = []

        def make_title(subj: str) -> str:
            variant = rng.choice(["Intro to", "Foundations of", "Advanced", "Applied", "Practical"])
            t = f"{variant} {subj}"
            idx = 2
            name = t
            while name in titles:
                idx += 1
                name = f"{t} {idx}"
            titles.add(name)
            return name

        # Ensure each instructor owns at least one course
        remaining = courses_n
        owner_to_quota: dict[int, int] = {u.id: 0 for u in instructors}
        # assign 1 first
        for u in instructors:
            if remaining <= 0:
                break
            subj = rng.choice(SUBJECTS)
            title = make_title(subj)
            desc = f"A concise, hands-on course covering core {subj.lower()} topics with practical exercises."
            c = Course.objects.create(owner=u, title=title, description=desc)
            courses.append(c)
            owner_to_quota[u.id] += 1
            remaining -= 1
        # distribute the rest ensuring each instructor max 3
        eligible = [u for u in instructors for _ in range(2)]  # roughly allow up to 3 total
        rng.shuffle(eligible)
        idx = 0
        while remaining > 0 and eligible:
            u = eligible[idx % len(eligible)]
            if owner_to_quota.get(u.id, 0) >= 3:
                idx += 1
                continue
            subj = rng.choice(SUBJECTS)
            title = make_title(subj)
            desc = (
                f"Explore intermediate {subj.lower()} concepts through projects and case studies."
            )
            c = Course.objects.create(owner=u, title=title, description=desc)
            courses.append(c)
            owner_to_quota[u.id] = owner_to_quota.get(u.id, 0) + 1
            remaining -= 1
            idx += 1

        self.stdout.write("Enrolling students...")
        course_ids = [c.id for c in courses]
        for u in students:
            k = rng.randint(enrol_min, enrol_max)
            picks = rng.sample(course_ids, min(k, len(course_ids)))
            for cid in picks:
                try:
                    Enrolment.objects.create(course_id=cid, student=u)
                except Exception:
                    # Skip duplicates
                    pass

        # Optional fixture dump for portability to Render
        dump = (options.get("dump") or "").strip()
        if dump:
            dump_path = Path(dump)
            dump_path.parent.mkdir(parents=True, exist_ok=True)
            self.stdout.write(f"Writing fixture to {dump_path} ...")
            call_command(
                "dumpdata",
                "--exclude",
                "auth.permission",
                "--exclude",
                "contenttypes",
                "--indent",
                "2",
                stdout=open(dump_path, "w", encoding="utf-8"),
            )

        # Optional credentials export (plaintext)
        cred_path = (options.get("export_credentials") or "").strip()
        if cred_path:
            p = Path(cred_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["username", "email", "role", "id_code", "password"])
                for row in creds_rows:
                    w.writerow(row)
            self.stdout.write(
                self.style.WARNING(f"Plaintext credentials exported to {p}. Store securely.")
            )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: students={len(students)}, instructors={len(instructors)}, "
                f"courses={len(courses)}, enrolments={Enrolment.objects.count()}"
            )
        )

        # Create/reset admin if requested
        if bool(options.get("create_admin")):
            admin_username = (options.get("admin_username") or "admin").strip()
            admin_password = (options.get("admin_password") or "CM3035").strip()
            if not admin_username:
                raise CommandError("--admin-username cannot be empty")
            if not admin_password:
                raise CommandError("--admin-password cannot be empty")

            UserModel = get_user_model()
            admin_user = UserModel.objects.filter(username=admin_username).first()
            if admin_user:
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.email = admin_user.email or "admin@courpera.com"
                admin_user.set_password(admin_password)  # bypass validators intentionally
                admin_user.save(update_fields=["is_staff", "is_superuser", "email", "password"])
            else:
                # Use create_superuser path
                admin_user = UserModel.objects.create_superuser(
                    username=admin_username,
                    email="admin@courpera.com",
                    password=admin_password,
                )
            # Ensure profile exists for admin
            try:
                _ = admin_user.profile  # created by signal
            except Exception:
                UserProfile.objects.get_or_create(user=admin_user)
            self.stdout.write(
                self.style.WARNING(
                    f"Admin account ready: username='{admin_username}' password='{admin_password}'"
                )
            )
