from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('programs', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReviewSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('base_url', models.URLField()),
                ('is_active', models.BooleanField(default=True)),
                ('rate_limit_per_minute', models.IntegerField(default=10)),
            ],
            options={
                'verbose_name': 'מקור ביקורות',
                'verbose_name_plural': 'מקורות ביקורות',
            },
        ),
        migrations.CreateModel(
            name='ReviewSnippet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_slug', models.SlugField(max_length=100)),
                ('source_url', models.URLField()),
                ('external_id', models.CharField(max_length=300)),
                ('raw_text', models.TextField()),
                ('language', models.CharField(default='he', max_length=5)),
                ('posted_at', models.DateTimeField(blank=True, null=True)),
                ('scraped_at', models.DateTimeField(auto_now_add=True)),
                ('author_handle', models.CharField(blank=True, max_length=200)),
                ('metadata', models.JSONField(default=dict)),
            ],
            options={
                'verbose_name': 'קטע ביקורת',
                'verbose_name_plural': 'קטעי ביקורת',
            },
        ),
        migrations.CreateModel(
            name='ProgramSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('summary_he', models.TextField()),
                ('pros_he', models.JSONField(default=list)),
                ('cons_he', models.JSONField(default=list)),
                ('themes_breakdown', models.JSONField()),
                ('snippet_count', models.IntegerField()),
                ('last_generated_at', models.DateTimeField(auto_now=True)),
                ('program', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='summary', to='programs.program')),
            ],
            options={
                'verbose_name': 'סיכום תוכנית',
                'verbose_name_plural': 'סיכומי תוכניות',
            },
        ),
        migrations.CreateModel(
            name='ReviewAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sentiment', models.FloatField()),
                ('themes', models.JSONField()),
                ('summary_he', models.TextField()),
                ('embedding', models.BinaryField(blank=True, null=True)),
                ('analyzed_at', models.DateTimeField(auto_now_add=True)),
                ('model_version', models.CharField(max_length=50)),
                ('snippet', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='analysis', to='reviews.reviewsnippet')),
            ],
            options={
                'verbose_name': 'ניתוח ביקורת',
                'verbose_name_plural': 'ניתוחי ביקורות',
            },
        ),
        migrations.CreateModel(
            name='RawScrape',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField()),
                ('raw_content', models.TextField()),
                ('scraped_at', models.DateTimeField(auto_now_add=True)),
                ('processing_status', models.CharField(choices=[('pending', 'Pending'), ('processed', 'Processed'), ('failed', 'Failed'), ('skipped', 'Skipped')], default='pending', max_length=20)),
                ('error', models.TextField(blank=True)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='raw_scrapes', to='reviews.reviewsource')),
            ],
            options={
                'verbose_name': 'גרידה גולמית',
                'verbose_name_plural': 'גרידות גולמיות',
            },
        ),
        migrations.CreateModel(
            name='ProgramReviewLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('confidence', models.FloatField()),
                ('method', models.CharField(max_length=50)),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_links', to='programs.program')),
                ('snippet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='program_links', to='reviews.reviewsnippet')),
            ],
            options={
                'verbose_name': 'קישור ביקורת לתוכנית',
                'verbose_name_plural': 'קישורי ביקורת לתוכניות',
                'constraints': [models.UniqueConstraint(fields=('snippet', 'program'), name='unique_link_snippet_program')],
            },
        ),
        migrations.AddIndex(
            model_name='reviewsnippet',
            index=models.Index(fields=['posted_at'], name='reviews_rev_posted__c1cca0_idx'),
        ),
        migrations.AddIndex(
            model_name='reviewsnippet',
            index=models.Index(fields=['scraped_at'], name='reviews_rev_scraped_7023b6_idx'),
        ),
        migrations.AddConstraint(
            model_name='reviewsnippet',
            constraint=models.UniqueConstraint(fields=('source_slug', 'external_id'), name='unique_snippet_source_external_id'),
        ),
        migrations.AddIndex(
            model_name='rawscrape',
            index=models.Index(fields=['processing_status', 'scraped_at'], name='reviews_raw_process_81fc79_idx'),
        ),
    ]
