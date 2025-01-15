-- Create occupational_adjustments table
CREATE TABLE IF NOT EXISTS occupational_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rating_percent REAL,
    c REAL,
    d REAL,
    e REAL,
    f REAL,
    g REAL,
    h REAL,
    i REAL,
    j REAL
);

-- Create occupations table
CREATE TABLE IF NOT EXISTS occupations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_number INTEGER,
    occupation_title TEXT,
    industry TEXT
);

-- Create variants table
CREATE TABLE IF NOT EXISTS variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    body_part TEXT,
    impairment_code TEXT,
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
    group_290 TEXT
);

-- Create variants_2 table
CREATE TABLE IF NOT EXISTS variants_2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    body_part TEXT,
    impairment_code TEXT,
    group_310 TEXT,
    group_311 TEXT,
    group_320 TEXT,
    group_321 TEXT,
    group_322 TEXT,
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

-- Create age_adjustment table
CREATE TABLE IF NOT EXISTS age_adjustment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wpi_percent REAL,
    "21_and_under" REAL,
    "22_to_26" REAL,
    "27_to_31" REAL,
    "32_to_36" REAL,
    "37_to_41" REAL,
    "42_to_46" REAL,
    "47_to_51" REAL,
    "52_to_56" REAL,
    "57_to_61" REAL,
    "62_and_over" REAL
);
