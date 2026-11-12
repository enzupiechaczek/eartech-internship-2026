
from django.urls import path

from . import views

urlpatterns = [
    path(
        "book/<int:doctor_id>/",
        views.book,
        name="book_appointment",
    ),
    path(
        "pending/",
        views.pending_requests,
        name="pending_requests",
    ),
]
