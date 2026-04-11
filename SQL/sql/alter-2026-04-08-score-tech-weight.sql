ALTER TABLE `score_model_tech_weight`
  ADD COLUMN `national_tech_honor` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '科技荣誉（国家级）' AFTER `national_provincial_award`,
  ADD COLUMN `provincial_tech_honor` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '科技荣誉（省级）' AFTER `national_tech_honor`,
  ADD COLUMN `medical_ai_model_filing` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '算法备案的医疗大模型' AFTER `provincial_tech_honor`,
  ADD COLUMN `high_quality_dataset` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '高质量数据集' AFTER `medical_ai_model_filing`;

UPDATE `score_model_tech_weight`
SET
  `national_tech_honor` = CASE WHEN `national_tech_honor` = 0 THEN 20.00 ELSE `national_tech_honor` END,
  `provincial_tech_honor` = CASE WHEN `provincial_tech_honor` = 0 THEN 15.00 ELSE `provincial_tech_honor` END,
  `medical_ai_model_filing` = CASE WHEN `medical_ai_model_filing` = 0 THEN 10.00 ELSE `medical_ai_model_filing` END,
  `high_quality_dataset` = CASE WHEN `high_quality_dataset` = 0 THEN 10.00 ELSE `high_quality_dataset` END;
