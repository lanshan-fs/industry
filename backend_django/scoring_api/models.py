from django.db import models


class ScoreResult(models.Model):
    enterprise_credit_code = models.CharField(max_length=18, primary_key=True, db_column="enterprise_credit_code")
    company_name = models.CharField(max_length=255, blank=True, null=True, db_column="company_name")
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="total_score")
    basic_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="basic_score")
    tech_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="tech_score")
    professional_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="professional_score")
    created_at = models.DateTimeField(db_column="created_at")
    updated_at = models.DateTimeField(db_column="updated_at")

    class Meta:
        managed = False
        db_table = "scoring_scoreresult"


class ScoreIndustryPath(models.Model):
    industry_path = models.CharField(max_length=255, primary_key=True, db_column="industry_path")
    path_level = models.SmallIntegerField(blank=True, null=True, db_column="path_level")
    avg_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column="avg_score")
    company_count = models.IntegerField(blank=True, null=True, db_column="company_count")

    class Meta:
        managed = False
        db_table = "score_industry_path"


class ScoreLog(models.Model):
    id = models.BigAutoField(primary_key=True, db_column="id")
    enterprise_credit_code = models.CharField(max_length=18, db_column="enterprise_credit_code")
    enterprise_name = models.CharField(max_length=255, blank=True, null=True, db_column="enterprise_name")
    score_type = models.CharField(max_length=20, blank=True, null=True, db_column="score_type")
    score_value = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, db_column="score_value")
    description = models.TextField(blank=True, null=True, db_column="description")
    created_at = models.DateTimeField(blank=True, null=True, db_column="created_at")

    class Meta:
        managed = False
        db_table = "scoring_scorelog"
