from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()
PASSWORD = "pass12345"


class RoleAccessTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            "student1", password=PASSWORD, role=User.Role.STUDENT)
        self.instructor = User.objects.create_user(
            "teacher1", password=PASSWORD, role=User.Role.INSTRUCTOR)
        self.admin = User.objects.create_user(
            "admin1", password=PASSWORD, role=User.Role.INSTRUCTOR,
            is_staff=True, is_superuser=True)

    # STEP 1: log in as each role
    def login_as(self, user):
        client = Client()
        self.assertTrue(client.login(username=user.username, password=PASSWORD))
        return client

    # STEP 2: forbidden pages -> 302 / 403
    def test_anonymous_redirected_from_studio(self):
        self.assertEqual(Client().get(reverse("studio")).status_code, 302)

    def test_anonymous_redirected_from_student_dashboard(self):
        response = Client().get(reverse("enrollments:student_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_anonymous_redirected_from_course_create(self):
        self.assertEqual(Client().get(reverse("courses:course_create")).status_code, 302)

    def test_student_forbidden_from_studio(self):
        response = self.login_as(self.student).get(reverse("studio"))
        self.assertEqual(response.status_code, 403)

    def test_student_forbidden_from_course_create(self):
        response = self.login_as(self.student).get(reverse("courses:course_create"))
        self.assertEqual(response.status_code, 403)

    def test_instructor_forbidden_from_student_dashboard(self):
        response = self.login_as(self.instructor).get(reverse("enrollments:student_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_student_forbidden_from_admin(self):
        response = self.login_as(self.student).get("/admin/")
        self.assertIn(response.status_code, [302, 403])

    # STEP 3: allowed pages -> 200
    def test_public_pages_ok_for_anonymous(self):
        for name in ["home", "about", "login", "register", "courses:list"]:
            with self.subTest(page=name):
                self.assertEqual(Client().get(reverse(name)).status_code, 200)

    def test_student_can_open_dashboard(self):
        response = self.login_as(self.student).get(reverse("enrollments:student_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_instructor_can_open_studio(self):
        self.assertEqual(self.login_as(self.instructor).get(reverse("studio")).status_code, 200)

    def test_instructor_can_open_course_create(self):
        response = self.login_as(self.instructor).get(reverse("courses:course_create"))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_open_admin(self):
        self.assertEqual(self.login_as(self.admin).get("/admin/").status_code, 200)