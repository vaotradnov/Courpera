# Courpera

Courpera is a server‑rendered e‑learning web application built with Django. It provides user accounts (students and teachers), course authoring and enrolment, materials upload, course feedback, status updates, notifications, search, and real‑time messaging.

Key Features
- User accounts and roles (students/teachers)
- Courses and enrolments with role‑based access
- Materials upload with server‑side validation
- Course feedback (rating and comments) and status updates
- Notifications (recent popover and full list)
- Search for people and courses
- Real‑time messaging via WebSockets (course rooms and direct messages)
- REST API with OpenAPI documentation

Technology Stack
- Python and Django (server‑rendered templates and forms)
- Django REST Framework (versioned REST API)
- drf‑spectacular (OpenAPI/Swagger/Redoc)
- Django Channels + Redis (WebSockets)
- SQLite by default; WhiteNoise for static files
- Optional enhancements: HTMX for progressive enhancement, DiceBear avatars, Google reCAPTCHA v3 on registration, and iCalendar (ICS) export for events

Design & Accessibility
- Accessible, semantic HTML with a lightweight design system (CSS tokens and base styles)

UI Overhaul (Stage 14)
- Direction: Coursera‑inspired information architecture and visual patterns while remaining brand‑neutral.
- Header & Navigation: prominent global search; an “Explore” menu for subjects; clear CTAs (Join/Enrol); profile menu and notifications grouped to the right.
- Course Cards: responsive grid; card shows title, partner logo/name, instructor, rating, level, language/subtitles; consistent spacing and hover states; keyboard focus ring.
- Course Detail: hero panel with course title, partner, outcomes, flexible deadlines badge, and primary “Enrol for free” CTA; syllabus as an accordion; instructor section and FAQs below; sticky CTA on mobile.
- Filters & Discovery: facets for subject, level, language, duration with clear chips and reset.
- Components: buttons (primary/secondary/link), inputs, toasts/messages, popovers (notifications), accordions (syllabus), skeleton loaders.
- Design Tokens (examples):
  - Colours: --cp-colour-primary: #2A73CC; --cp-colour-accent: #1264A3; neutrals #111/#444/#777/#EEE; success/warn/error palette.
  - Spacing: 4/8/12/16/24/32 px scale; radii 4/8; shadows for elevation 1–3.
  - Typography: system UI stack (Segoe UI, Roboto, Helvetica, Arial, sans-serif); line‑height 1.5; headings scaled down on mobile.
  - Breakpoints: 480 / 768 / 1024 / 1280 px.
- Accessibility: skip‑link, landmark roles, labelled controls, visible focus; nav/menus/accordions ARIA attributes; keyboard operation of search and menus.
- CSP: no inline scripts/styles; all assets served from static/; connect‑src allows ws/wss; img‑src allows DiceBear and data:.

Verification
- Run: `pytest -m "not ws"` for quick UI smoke; `pytest -m security` for CSP/permissions.
- Manual: compare header/search prominence, Explore menu, card grid, hero CTA, syllabus accordion against Coursera’s layout patterns.
