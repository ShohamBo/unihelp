from rest_framework import serializers
from institutions.models import Institution


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = ['id', 'slug', 'name_he', 'name_en', 'type', 'city', 'website', 'logo_url']
