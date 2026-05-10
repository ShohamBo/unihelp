from django.urls import path
from .views import ReviewSnippetBulkView

urlpatterns = [
    path("snippets/bulk/", ReviewSnippetBulkView.as_view(), name="review_snippets_bulk"),
]
