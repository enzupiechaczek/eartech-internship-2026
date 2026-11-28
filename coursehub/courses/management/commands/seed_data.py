from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from courses.models import Category, Course, Lesson, LessonProgress, Module
from enrollments.models import Enrollment
from reviews.models import Review

User = get_user_model()


class Command(BaseCommand):
    help = "Populate the database with realistic demo data for CourseHub."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing seeded demo records before recreating them.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing demo data..."))
            Review.objects.all().delete()
            LessonProgress.objects.all().delete()
            Enrollment.objects.all().delete()
            Lesson.objects.all().delete()
            Module.objects.all().delete()
            Course.objects.all().delete()
            Category.objects.all().delete()
            User.objects.filter(
                username__in=[
                    "admin",
                    "instructor_sarah",
                    "instructor_omar",
                    "student_alex",
                    "student_maya",
                ]
            ).delete()

        # 1. Create Users (Admin, Instructors, Students)
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@coursehub.local",
                "first_name": "Platform",
                "last_name": "Admin",
                "role": User.Role.INSTRUCTOR,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin_user.set_password("Admin1234!")
            admin_user.save()

        sarah, created = User.objects.get_or_create(
            username="instructor_sarah",
            defaults={
                "email": "sarah@coursehub.local",
                "first_name": "Sarah",
                "last_name": "Jenkins",
                "role": User.Role.INSTRUCTOR,
            },
        )
        if created:
            sarah.set_password("Demo1234!")
            sarah.save()

        omar, created = User.objects.get_or_create(
            username="instructor_omar",
            defaults={
                "email": "omar@coursehub.local",
                "first_name": "Omar",
                "last_name": "Hassan",
                "role": User.Role.INSTRUCTOR,
            },
        )
        if created:
            omar.set_password("Demo1234!")
            omar.save()

        alex, created = User.objects.get_or_create(
            username="student_alex",
            defaults={
                "email": "alex@coursehub.local",
                "first_name": "Alex",
                "last_name": "Rivera",
                "role": User.Role.STUDENT,
            },
        )
        if created:
            alex.set_password("Demo1234!")
            alex.save()

        maya, created = User.objects.get_or_create(
            username="student_maya",
            defaults={
                "email": "maya@coursehub.local",
                "first_name": "Maya",
                "last_name": "Lin",
                "role": User.Role.STUDENT,
            },
        )
        if created:
            maya.set_password("Demo1234!")
            maya.save()

        # 2. Create Categories
        categories = {}
        for cat_name in [
            "Web Development",
            "Python & Backend",
            "Cybersecurity",
            "Data Science & AI",
        ]:
            cat, _ = Category.objects.get_or_create(name=cat_name)
            categories[cat_name] = cat

        # 3. Create Courses, Modules, and Lessons
        courses_spec = [
            {
                "title": "Full-Stack Web Development with Django",
                "subtitle": "Build, secure, and deploy production-ready web apps from scratch.",
                "description": (
                    "Master Django models, class-based views, authentication, role-based access "
                    "control, and clean responsive templates by building real projects."
                ),
                "category": categories["Web Development"],
                "instructor": sarah,
                "price": Decimal("49.99"),
                "status": Course.Status.PUBLISHED,
                "modules": [
                    {
                        "title": "Module 1: Django Architecture & Models",
                        "order": 1,
                        "lessons": [
                            {
                                "title": "Project Setup & MTV Pattern",
                                "notes": "Understanding Models, Templates, and Views in Django.",
                                "video_url": "https://vimeo.com/76979871",
                                "order": 1,
                            },
                            {
                                "title": "Designing Relational Database Models",
                                "notes": "Working with ForeignKey, ManyToManyField, and migrations.",
                                "video_url": "https://vimeo.com/1084537",
                                "order": 2,
                            },
                        ],
                    },
                    {
                        "title": "Module 2: Authentication & Permissions",
                        "order": 2,
                        "lessons": [
                            {
                                "title": "Custom User Models & Roles",
                                "notes": "Extending AbstractUser to separate Students and Instructors.",
                                "video_url": "https://vimeo.com/76979871",
                                "order": 1,
                            },
                            {
                                "title": "Protecting Views & Ownership Checks",
                                "notes": "Using LoginRequiredMixin and custom decorators safely.",
                                "video_url": "https://vimeo.com/1084537",
                                "order": 2,
                            },
                        ],
                    },
                ],
            },
            {
                "title": "Python Programming Masterclass: Zero to Hero",
                "subtitle": "Learn clean Python syntax, data structures, and automation.",
                "description": (
                    "A hands-on introduction to modern Python covering functions, OOP, "
                    "file handling, and writing maintainable code."
                ),
                "category": categories["Python & Backend"],
                "instructor": sarah,
                "price": Decimal("0.00"),
                "status": Course.Status.PUBLISHED,
                "modules": [
                    {
                        "title": "Module 1: Core Python Fundamentals",
                        "order": 1,
                        "lessons": [
                            {
                                "title": "Variables, Types, and Control Flow",
                                "notes": "Writing readable conditional logic and loops in Python.",
                                "video_url": "https://vimeo.com/76979871",
                                "order": 1,
                            },
                            {
                                "title": "Lists, Dictionaries, and Comprehensions",
                                "notes": "Choosing the right built-in data structure for performance.",
                                "video_url": "https://vimeo.com/1084537",
                                "order": 2,
                            },
                        ],
                    },
                ],
            },
            {
                "title": "Practical Ethical Hacking & Web Security",
                "subtitle": "Identify and patch OWASP Top 10 vulnerabilities in web applications.",
                "description": (
                    "Learn how attackers exploit SQL injection, XSS, CSRF, and broken access "
                    "control—and how developers defend against them."
                ),
                "category": categories["Cybersecurity"],
                "instructor": omar,
                "price": Decimal("59.99"),
                "status": Course.Status.PUBLISHED,
                "modules": [
                    {
                        "title": "Module 1: Web Application Reconnaissance",
                        "order": 1,
                        "lessons": [
                            {
                                "title": "HTTP Basics & Attack Surface Mapping",
                                "notes": "Inspecting headers, cookies, and session tokens.",
                                "video_url": "https://vimeo.com/76979871",
                                "order": 1,
                            },
                            {
                                "title": "Preventing Broken Access Control (IDOR)",
                                "notes": "Enforcing server-side object ownership on every request.",
                                "video_url": "https://vimeo.com/1084537",
                                "order": 2,
                            },
                        ],
                    },
                ],
            },
            {
                "title": "Applied Machine Learning with Python (Draft)",
                "subtitle": "Supervised learning workflows with Scikit-Learn and Pandas.",
                "description": (
                    "Upcoming course covering data preprocessing, feature engineering, "
                    "and model evaluation metrics."
                ),
                "category": categories["Data Science & AI"],
                "instructor": sarah,
                "price": Decimal("39.99"),
                "status": Course.Status.DRAFT,
                "modules": [
                    {
                        "title": "Module 1: Data Preparation",
                        "order": 1,
                        "lessons": [
                            {
                                "title": "Cleaning Datasets with Pandas",
                                "notes": "Handling missing values and encoding categorical features.",
                                "video_url": "https://vimeo.com/76979871",
                                "order": 1,
                            },
                        ],
                    },
                ],
            },
        ]

        created_courses = {}
        for c_data in courses_spec:
            course, _ = Course.objects.update_or_create(
                title=c_data["title"],
                instructor=c_data["instructor"],
                defaults={
                    "subtitle": c_data["subtitle"],
                    "description": c_data["description"],
                    "category": c_data["category"],
                    "price": c_data["price"],
                    "status": c_data["status"],
                },
            )
            created_courses[course.title] = course

            for m_data in c_data["modules"]:
                module, _ = Module.objects.update_or_create(
                    course=course,
                    title=m_data["title"],
                    defaults={"order": m_data["order"]},
                )
                for l_data in m_data["lessons"]:
                    Lesson.objects.update_or_create(
                        module=module,
                        title=l_data["title"],
                        defaults={
                            "notes": l_data["notes"],
                            "video_url": l_data["video_url"],
                            "order": l_data["order"],
                        },
                    )

        # 4. Create Enrollments, Lesson Progress, and Reviews
        django_course = created_courses["Full-Stack Web Development with Django"]
        python_course = created_courses["Python Programming Masterclass: Zero to Hero"]
        security_course = created_courses["Practical Ethical Hacking & Web Security"]

        # Alex enrolled in Django (50% progress) & Python (100% progress + review)
        Enrollment.objects.get_or_create(student=alex, course=django_course)
        Enrollment.objects.get_or_create(student=alex, course=python_course)

        django_lessons = list(Lesson.objects.filter(module__course=django_course))
        for lesson in django_lessons[:2]:
            LessonProgress.objects.get_or_create(student=alex, lesson=lesson)

        python_lessons = list(Lesson.objects.filter(module__course=python_course))
        for lesson in python_lessons:
            LessonProgress.objects.get_or_create(student=alex, lesson=lesson)

        Review.objects.update_or_create(
            course=python_course,
            student=alex,
            defaults={
                "rating": 5,
                "comment": "Clear explanations and practical examples. Great starting point!",
            },
        )

        # Maya enrolled in Security (50% progress) + review on Django after completing earlier
        Enrollment.objects.get_or_create(student=maya, course=security_course)
        security_lessons = list(Lesson.objects.filter(module__course=security_course))
        if security_lessons:
            LessonProgress.objects.get_or_create(student=maya, lesson=security_lessons[0])

        Enrollment.objects.get_or_create(student=maya, course=django_course)
        Review.objects.update_or_create(
            course=django_course,
            student=maya,
            defaults={
                "rating": 5,
                "comment": "Best hands-on Django architecture course. Everything clicks together.",
            },
        )

        self.stdout.write(self.style.SUCCESS("Successfully seeded CourseHub demo data!"))
        self.stdout.write("Demo Accounts:")
        self.stdout.write("  - Admin:      admin / Admin1234!")
        self.stdout.write("  - Instructor: instructor_sarah / Demo1234!")
        self.stdout.write("  - Instructor: instructor_omar / Demo1234!")
        self.stdout.write("  - Student:    student_alex / Demo1234!")
        self.stdout.write("  - Student:    student_maya / Demo1234!")