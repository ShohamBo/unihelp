from django.urls import path
from .views import ProgramBulkView, CourseBulkView, ProgramListView, ProgramDetailView

urlpatterns = [
    path('', ProgramListView.as_view(), name='programs_list'),
    path('bulk/', ProgramBulkView.as_view(), name='programs_bulk'),
    path('courses/bulk/', CourseBulkView.as_view(), name='courses_bulk'),
    path('<slug:institution>/<slug:program>/', ProgramDetailView.as_view(), name='program_detail'),
]
