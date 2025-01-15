-- Import occupational adjustments data
COPY workers_comp.occupational_adjustments(rating_percent, c, d, e, f, g, h, i, j)
FROM '/Volumes/DevDrive/Development/Projects/wcpython/data/sql/occupational_adjustments_rows.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');

-- Import occupations data
COPY workers_comp.occupations(group_number, occupation_title, industry)
FROM '/Volumes/DevDrive/Development/Projects/wcpython/data/sql/occupations_rows.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');

-- Create a temporary table for variants data
CREATE TEMP TABLE temp_variants_1 (
    Body_Part TEXT,
    Impairment_Code TEXT,
    group_110 TEXT,
    group_111 TEXT,
    group_112 TEXT,
    group_120 TEXT,
    group_210 TEXT,
    group_211 TEXT,
    group_212 TEXT,
    group_213 TEXT,
    group_214 TEXT,
    group_220 TEXT,
    group_221 TEXT,
    group_230 TEXT,
    group_240 TEXT,
    group_250 TEXT,
    group_251 TEXT,
    group_290 TEXT,
    group_310 TEXT,
    group_311 TEXT,
    group_320 TEXT,
    group_321 TEXT,
    group_322 TEXT
);

CREATE TEMP TABLE temp_variants_2 (
    Body_Part TEXT,
    Impairment_Code TEXT,
    group_330 TEXT,
    group_331 TEXT,
    group_332 TEXT,
    group_340 TEXT,
    group_341 TEXT,
    group_350 TEXT,
    group_351 TEXT,
    group_360 TEXT,
    group_370 TEXT,
    group_380 TEXT,
    group_390 TEXT,
    group_420 TEXT,
    group_430 TEXT,
    group_460 TEXT,
    group_470 TEXT,
    group_480 TEXT,
    group_481 TEXT,
    group_482 TEXT,
    group_490 TEXT,
    group_491 TEXT,
    group_492 TEXT,
    group_493 TEXT,
    group_560 TEXT,
    group_590 TEXT
);

-- Import variants data into temp tables
COPY temp_variants_1
FROM '/Volumes/DevDrive/Development/Projects/wcpython/data/sql/variants_rows.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');

COPY temp_variants_2
FROM '/Volumes/DevDrive/Development/Projects/wcpython/data/sql/variants_2_rows.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');

-- Merge variants data into final table
INSERT INTO workers_comp.variants (
    body_part,
    impairment_code,
    group_110, group_111, group_112, group_120, group_210, group_211, group_212, group_213, group_214,
    group_220, group_221, group_230, group_240, group_250, group_251, group_290, group_310, group_311,
    group_320, group_321, group_322, group_330, group_331, group_332, group_340, group_341, group_350,
    group_351, group_360, group_370, group_380, group_390, group_420, group_430, group_460, group_470,
    group_480, group_481, group_482, group_490, group_491, group_492, group_493, group_560, group_590
)
SELECT 
    v1.Body_Part,
    v1.Impairment_Code,
    v1.group_110, v1.group_111, v1.group_112, v1.group_120, v1.group_210, v1.group_211, v1.group_212,
    v1.group_213, v1.group_214, v1.group_220, v1.group_221, v1.group_230, v1.group_240, v1.group_250,
    v1.group_251, v1.group_290, v1.group_310, v1.group_311, v1.group_320, v1.group_321, v1.group_322,
    v2.group_330, v2.group_331, v2.group_332, v2.group_340, v2.group_341, v2.group_350, v2.group_351,
    v2.group_360, v2.group_370, v2.group_380, v2.group_390, v2.group_420, v2.group_430, v2.group_460,
    v2.group_470, v2.group_480, v2.group_481, v2.group_482, v2.group_490, v2.group_491, v2.group_492,
    v2.group_493, v2.group_560, v2.group_590
FROM temp_variants_1 v1
JOIN temp_variants_2 v2 ON v1.Body_Part = v2.Body_Part AND v1.Impairment_Code = v2.Impairment_Code;

-- Drop temporary tables
DROP TABLE temp_variants_1;
DROP TABLE temp_variants_2;

-- Import age adjustment data
COPY workers_comp.age_adjustment(wpi_percent, "21_and_under", "22_to_26", "27_to_31", "32_to_36", "37_to_41", "42_to_46", "47_to_51", "52_to_56", "57_to_61", "62_and_over")
FROM '/Volumes/DevDrive/Development/Projects/wcpython/data/sql/age_adjustment_temp.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');
