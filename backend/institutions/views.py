from rest_framework import generics
from institutions.models import Institution
from institutions.serializers import InstitutionSerializer


class InstitutionListView(generics.ListAPIView):
    queryset = Institution.objects.filter(is_active=True).order_by('name_he')
    serializer_class = InstitutionSerializer
    pagination_class = None  # return all institutions in one response
