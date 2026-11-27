from types import SimpleNamespace

from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class CourseCatalogTemplateTests(SimpleTestCase):
    """Frontend contract for the catalogue pagination UI."""

    @staticmethod
    def make_course(pk, category):
        instructor = SimpleNamespace(
            username="yousef",
            get_full_name=lambda: "Yousef",
        )
        return SimpleNamespace(
            pk=pk,
            title=f"Course {pk}",
            subtitle="A useful course",
            thumbnail="",
            category=category,
            instructor=instructor,
            price=0,
        )

    def test_pagination_ui_uses_contract_context_variables(self):
        category = SimpleNamespace(pk=1, name="Programming")
        courses = [self.make_course(pk, category) for pk in range(1, 11)]
        paginator = Paginator(courses, 9)
        page_obj = paginator.get_page(1)

        html = render_to_string(
            "courses/course_list.html",
            {
                "page_obj": page_obj,
                "paginator": paginator,
                "search_query": "Django",
                "selected_category": category,
                "categories": [category],
            },
        )

        self.assertIn('value="Django"', html)
        self.assertIn("Page 1 of 2", html)
        self.assertIn('aria-current="page"', html)
        self.assertIn("q=Django&amp;category=1&amp;page=2", html)
        self.assertIn(
            '<li class="page-item disabled">'
            '<span class="page-link">Previous</span></li>',
            html,
        )
