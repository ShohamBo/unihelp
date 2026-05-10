from rest_framework import serializers
from django.db import models

from programs.models import Program, AdmissionRequirement
from reviews.models import ProgramSummary, ReviewSnippet


class AdmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionRequirement
        fields = [
            'psychometric_min', 'sechem_min',
            'bagrut_requirements_he', 'additional_requirements_he',
            'last_year_threshold',
        ]


class ProgramSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgramSummary
        fields = ['summary_he', 'pros_he', 'cons_he', 'themes_breakdown', 'snippet_count', 'last_generated_at']


class SnippetSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name')

    class Meta:
        model = ReviewSnippet
        fields = ['id', 'raw_text', 'posted_at', 'language', 'metadata', 'source_name']


class ProgramListSerializer(serializers.ModelSerializer):
    institution_slug = serializers.CharField(source='institution.slug')
    institution_name_he = serializers.CharField(source='institution.name_he')

    class Meta:
        model = Program
        fields = [
            'id', 'slug', 'name_he', 'name_en', 'degree_level',
            'duration_years', 'total_credits', 'is_dual_major', 'is_extended',
            'institution_slug', 'institution_name_he',
        ]


class ProgramDetailSerializer(serializers.ModelSerializer):
    institution_slug = serializers.CharField(source='institution.slug')
    institution_name_he = serializers.CharField(source='institution.name_he')
    institution_city = serializers.CharField(source='institution.city')
    faculty_name_he = serializers.SerializerMethodField()
    admission = AdmissionSerializer(read_only=True)
    summary = ProgramSummarySerializer(read_only=True)
    top_snippets = serializers.SerializerMethodField()

    class Meta:
        model = Program
        fields = [
            'id', 'slug', 'name_he', 'name_en', 'degree_level',
            'duration_years', 'total_credits', 'is_dual_major', 'is_extended',
            'description_he', 'canonical_url',
            'institution_slug', 'institution_name_he', 'institution_city',
            'faculty_name_he', 'admission', 'summary', 'top_snippets',
        ]

    def get_faculty_name_he(self, obj):
        return obj.faculty.name_he if obj.faculty else None

    def get_top_snippets(self, obj):
        from reviews.models import ProgramReviewLink
        links = (
            ProgramReviewLink.objects
            .filter(program=obj)
            .select_related('snippet', 'snippet__source')
            .order_by('-confidence')[:5]
        )
        return SnippetSerializer([link.snippet for link in links], many=True).data
