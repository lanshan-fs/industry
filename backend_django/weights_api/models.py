from django.db import models


class ScoreModelTotalWeight(models.Model):
    model_id = models.BigAutoField(primary_key=True, db_column="model_id")
    model_name = models.CharField(max_length=100, db_column="model_name")
    model_weight = models.DecimalField(max_digits=5, decimal_places=2, db_column="model_weight")

    class Meta:
        managed = False
        db_table = "score_model_total_weight"


class ScoreModelBasicWeight(models.Model):
    model_id = models.BigAutoField(primary_key=True, db_column="model_id")
    model_name = models.CharField(max_length=100, db_column="model_name")
    established_year = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="established_year")
    registered_capital = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="registered_capital")
    actual_paid_capital = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="actual_paid_capital")
    company_type = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="company_type")
    enterprise_size_type = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="enterprise_size_type")
    social_security_count = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="social_security_count")
    website = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="website")
    business_scope = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="business_scope")
    tax_rating = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="tax_rating")
    tax_type = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="tax_type")
    funding_round = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="funding_round")
    patent_type = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="patent_type")
    software_copyright = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="software_copyright")
    technology_enterprise = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="technology_enterprise")

    class Meta:
        managed = False
        db_table = "score_model_basic_weight"


class ScoreModelTechWeight(models.Model):
    model_id = models.BigAutoField(primary_key=True, db_column="model_id")
    model_name = models.CharField(max_length=100, db_column="model_name")
    tech_patent_type = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="tech_patent_type")
    patent_tech_attribute = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="patent_tech_attribute")
    tech_software_copyright = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="tech_software_copyright")
    software_copyright_tech_attribute = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="software_copyright_tech_attribute")
    tech_technology_enterprise = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="tech_technology_enterprise")
    industry_university_research = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="industry_university_research")
    national_provincial_award = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="national_provincial_award")
    national_tech_honor = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="national_tech_honor")
    provincial_tech_honor = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="provincial_tech_honor")
    medical_ai_model_filing = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="medical_ai_model_filing")
    high_quality_dataset = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="high_quality_dataset")

    class Meta:
        managed = False
        db_table = "score_model_tech_weight"


class ScoreModelProfessionalWeight(models.Model):
    model_id = models.BigAutoField(primary_key=True, db_column="model_id")
    model_name = models.CharField(max_length=100, db_column="model_name")
    industry_market_size = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="industry_market_size")
    industry_heat = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="industry_heat")
    industry_profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="industry_profit_margin")
    qualification = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="qualification")
    certificates = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="certificates")
    innovation = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="innovation")
    partnership_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="partnership_score")
    ranking = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column="ranking")

    class Meta:
        managed = False
        db_table = "score_model_professional_weight"
