from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Program',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('institution_slug', models.SlugField(max_length=100)),
                ('faculty_slug', models.SlugField(blank=True, max_length=100)),
                ('slug', models.SlugField()),
                ('name_he', models.CharField(max_length=300)),
                ('name_en', models.CharField(blank=True, max_length=300)),
                ('degree_level', models.CharField(choices=[('ba', 'תואר ראשון'), ('ma', 'תואר שני'), ('phd', 'דוקטורט')], max_length=5)),
                ('duration_years', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ('total_credits', models.IntegerField(blank=True, null=True)),
                ('is_dual_major', models.BooleanField(default=False)),
                ('is_extended', models.BooleanField(default=False)),
                ('description_he', models.TextField(blank=True)),
                ('canonical_url', models.URLField(blank=True)),
                ('last_scraped_at', models.DateTimeField(blank=True, null=True)),
                ('metadata', models.JSONField(default=dict)),
            ],
            options={
                'verbose_name': 'תוכנית',
                'verbose_name_plural': 'תוכניות',
            },
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('institution_slug', models.SlugField(max_length=100)),
                ('name_he', models.CharField(max_length=300)),
                ('name_en', models.CharField(blank=True, max_length=300)),
                ('course_code', models.CharField(blank=True, max_length=50)),
                ('credits', models.IntegerField(blank=True, null=True)),
                ('semester', models.CharField(blank=True, max_length=20)),
                ('is_mandatory', models.BooleanField(default=True)),
                ('description_he', models.TextField(blank=True)),
                ('metadata', models.JSONField(default=dict)),
                ('program', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='courses', to='programs.program')),
            ],
            options={
                'verbose_name': 'קורס',
                'verbose_name_plural': 'קורסים',
            },
        ),
        migrations.CreateModel(
            name='AdmissionRequirement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('psychometric_min', models.IntegerField(blank=True, null=True)),
                ('sechem_min', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('bagrut_requirements_he', models.TextField(blank=True)),
                ('additional_requirements_he', models.TextField(blank=True)),
                ('last_year_threshold', models.IntegerField(blank=True, null=True)),
                ('metadata', models.JSONField(default=dict)),
                ('program', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='admission', to='programs.program')),
            ],
            options={
                'verbose_name': 'דרישות קבלה',
                'verbose_name_plural': 'דרישות קבלה',
            },
        ),
        migrations.CreateModel(
            name='ProgramAlias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alias_text', models.CharField(max_length=300)),
                ('language', models.CharField(default='he', max_length=5)),
                ('source_type', models.CharField(choices=[('manual', 'Manual'), ('learned', 'Learned'), ('official', 'Official')], default='manual', max_length=20)),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='aliases', to='programs.program')),
            ],
            options={
                'verbose_name': 'כינוי תוכנית',
                'verbose_name_plural': 'כינויי תוכנית',
            },
        ),
        migrations.CreateModel(
            name='ProgramVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('academic_year', models.CharField(max_length=10)),
                ('raw_catalog_data', models.JSONField()),
                ('scraped_at', models.DateTimeField(auto_now_add=True)),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='programs.program')),
            ],
            options={
                'verbose_name': 'גרסת תוכנית',
                'verbose_name_plural': 'גרסאות תוכניות',
            },
        ),
        migrations.AddIndex(
            model_name='program',
            index=models.Index(fields=['institution_slug', 'degree_level'], name='programs_pr_institu_c8b548_idx'),
        ),
        migrations.AddIndex(
            model_name='program',
            index=models.Index(fields=['institution_slug'], name='programs_pr_institu_slug_idx'),
        ),
        migrations.AddConstraint(
            model_name='program',
            constraint=models.UniqueConstraint(fields=('institution_slug', 'slug'), name='unique_program_institution_slug'),
        ),
        migrations.AddConstraint(
            model_name='course',
            constraint=models.UniqueConstraint(condition=models.Q(('course_code__gt', '')), fields=('program', 'course_code'), name='unique_course_program_code'),
        ),
        migrations.AddConstraint(
            model_name='programalias',
            constraint=models.UniqueConstraint(fields=('program', 'alias_text'), name='unique_alias'),
        ),
        migrations.AddConstraint(
            model_name='programversion',
            constraint=models.UniqueConstraint(fields=('program', 'academic_year'), name='unique_version_program_year'),
        ),
    ]
