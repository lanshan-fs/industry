START TRANSACTION;

CREATE TEMPORARY TABLE tmp_delete_company_ids (
  company_id BIGINT PRIMARY KEY
);

INSERT INTO tmp_delete_company_ids (company_id) VALUES
  (26423),(26421),(26417),(26414),(26410),(26405),(26395),(26394),(26393),(26385),
  (26384),(26369),(26366),(26363),(26361),(26348),(26343),(26342),(26341),(26340),
  (26338),(26337),(26336),(26335),(26333),(26326),(26323),(26322),(26318),(26317),
  (26255),(26242),(26237),(26222),(26215),(26213),(26212),(26211),(26199),(26195),
  (26186),(26184),(26181),(26180),(26179),(26172),(26170),(26165),(26161),(26160),
  (26159),(26158),(26157),(26156),(26142),(26128),(26117),(26114),(26113),(26104),
  (26095),(26094),(26091),(26090),(26076),(26062),(26058),(26051),(26050),(26047),
  (26042),(26035),(26028),(26027),(26024),(26023),(26022),(26017),(26009),(26006),
  (26003),(25983),(25975),(25974),(25950),(25941),(25933),(25931),(25928),(25924),
  (25921),(25918),(25916),(25914),(25907),(25901),(25895),(25892),(25891),(25887);

DELETE ptm
FROM company_patent_patent_type_map AS ptm
JOIN company_patent AS p ON p.company_patent_id = ptm.company_patent_id
JOIN tmp_delete_company_ids AS d ON d.company_id = p.company_id;

DELETE pcm
FROM company_patent_company_map AS pcm
LEFT JOIN tmp_delete_company_ids AS d1 ON d1.company_id = pcm.company_id
LEFT JOIN company_patent AS p ON p.company_patent_id = pcm.company_patent_id
LEFT JOIN tmp_delete_company_ids AS d2 ON d2.company_id = p.company_id
WHERE d1.company_id IS NOT NULL OR d2.company_id IS NOT NULL;

DELETE cim
FROM category_industry_company_map AS cim
JOIN tmp_delete_company_ids AS d ON d.company_id = cim.company_id;

DELETE ca
FROM company_address AS ca
JOIN tmp_delete_company_ids AS d ON d.company_id = ca.company_id;

DELETE cbc
FROM company_bidding AS cbc
JOIN tmp_delete_company_ids AS d ON d.company_id = cbc.company_id;

DELETE cb
FROM company_branch AS cb
JOIN tmp_delete_company_ids AS d ON d.company_id = cb.company_id;

DELETE ccg
FROM company_change AS ccg
JOIN tmp_delete_company_ids AS d ON d.company_id = ccg.company_id;

DELETE ccr
FROM company_consumption_restriction AS ccr
JOIN tmp_delete_company_ids AS d ON d.company_id = ccr.company_id;

DELETE cci
FROM company_contact_info AS cci
JOIN tmp_delete_company_ids AS d ON d.company_id = cci.company_id;

DELETE ccp
FROM company_contact_phone AS ccp
JOIN tmp_delete_company_ids AS d ON d.company_id = ccp.company_id;

DELETE cc
FROM company_customer AS cc
LEFT JOIN tmp_delete_company_ids AS d1 ON d1.company_id = cc.company_id
LEFT JOIN tmp_delete_company_ids AS d2 ON d2.company_id = cc.customer_company_id
WHERE d1.company_id IS NOT NULL OR d2.company_id IS NOT NULL;

DELETE cec
FROM company_employee_count AS cec
JOIN tmp_delete_company_ids AS d ON d.company_id = cec.company_id;

DELETE cf
FROM company_financing AS cf
JOIN tmp_delete_company_ids AS d ON d.company_id = cf.company_id;

DELETE cfn
FROM company_former_name AS cfn
JOIN tmp_delete_company_ids AS d ON d.company_id = cfn.company_id;

DELETE cls
FROM company_listing_status AS cls
JOIN tmp_delete_company_ids AS d ON d.company_id = cls.company_id;

DELETE cp
FROM company_patent AS cp
JOIN tmp_delete_company_ids AS d ON d.company_id = cp.company_id;

DELETE cq
FROM company_qualification AS cq
JOIN tmp_delete_company_ids AS d ON d.company_id = cq.company_id;

DELETE crk
FROM company_ranking AS crk
JOIN tmp_delete_company_ids AS d ON d.company_id = crk.company_id;

DELETE crp
FROM company_recommended_phone AS crp
JOIN tmp_delete_company_ids AS d ON d.company_id = crp.company_id;

DELETE crt
FROM company_recruit AS crt
JOIN tmp_delete_company_ids AS d ON d.company_id = crt.company_id;

DELETE cr
FROM company_risk AS cr
JOIN tmp_delete_company_ids AS d ON d.company_id = cr.company_id;

DELETE csh
FROM company_shareholder AS csh
JOIN tmp_delete_company_ids AS d ON d.company_id = csh.company_id;

DELETE csc
FROM company_software_copyright AS csc
JOIN tmp_delete_company_ids AS d ON d.company_id = csc.company_id;

DELETE csd
FROM company_subdistrict AS csd
JOIN tmp_delete_company_ids AS d ON d.company_id = csd.company_id;

DELETE cs
FROM company_supplier AS cs
LEFT JOIN tmp_delete_company_ids AS d1 ON d1.company_id = cs.company_id
LEFT JOIN tmp_delete_company_ids AS d2 ON d2.company_id = cs.supplier_company_id
WHERE d1.company_id IS NOT NULL OR d2.company_id IS NOT NULL;

DELETE ctbi
FROM company_tag_batch_item AS ctbi
JOIN tmp_delete_company_ids AS d ON d.company_id = ctbi.company_id;

DELETE ctlc
FROM company_tag_llm_candidate AS ctlc
JOIN tmp_delete_company_ids AS d ON d.company_id = ctlc.company_id;

DELETE ctm
FROM company_tag_map AS ctm
JOIN tmp_delete_company_ids AS d ON d.company_id = ctm.company_id;

DELETE ctr
FROM company_trademark AS ctr
JOIN tmp_delete_company_ids AS d ON d.company_id = ctr.company_id;

DELETE cw
FROM company_website AS cw
JOIN tmp_delete_company_ids AS d ON d.company_id = cw.company_id;

DELETE cwc
FROM company_work_copyright AS cwc
JOIN tmp_delete_company_ids AS d ON d.company_id = cwc.company_id;

DELETE ssl
FROM scoring_scorelog AS ssl
JOIN tmp_delete_company_ids AS d ON d.company_id = ssl.enterprise_id;

DELETE ssr
FROM scoring_scoreresult AS ssr
JOIN tmp_delete_company_ids AS d ON d.company_id = ssr.enterprise_id;

DELETE cbc
FROM company_basic_count AS cbc
JOIN tmp_delete_company_ids AS d ON d.company_id = cbc.company_id;

DELETE cb
FROM company_basic AS cb
JOIN tmp_delete_company_ids AS d ON d.company_id = cb.company_id;

SELECT 'remaining_company_basic' AS metric, COUNT(*) AS total
FROM company_basic AS cb
JOIN tmp_delete_company_ids AS d ON d.company_id = cb.company_id
UNION ALL
SELECT 'remaining_company_tag_map' AS metric, COUNT(*) AS total
FROM company_tag_map AS ctm
JOIN tmp_delete_company_ids AS d ON d.company_id = ctm.company_id
UNION ALL
SELECT 'remaining_company_qualification' AS metric, COUNT(*) AS total
FROM company_qualification AS cq
JOIN tmp_delete_company_ids AS d ON d.company_id = cq.company_id
UNION ALL
SELECT 'remaining_company_recruit' AS metric, COUNT(*) AS total
FROM company_recruit AS crt
JOIN tmp_delete_company_ids AS d ON d.company_id = crt.company_id;

COMMIT;
