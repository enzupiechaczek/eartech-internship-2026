from django.test import TestCase
from django.urls import reverse


class CourseListViewTests(TestCase):
    def test_course_list_page_loads(self):
        response = self.client.get(reverse('courses:list'))
        self.assertEqual(response.status_code, 200)
# Create your tests here.
