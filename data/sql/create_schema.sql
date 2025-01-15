-- Create the workers_comp schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS workers_comp;

-- Create occupational_adjustments table
CREATE TABLE IF NOT EXISTS workers_comp.occupational_adjustments (
    id SERIAL PRIMARY KEY,
    rating_percent NUMERIC,
    c NUMERIC,
    d NUMERIC,
    e NUMERIC,
    f NUMERIC,
    g NUMERIC,
    h NUMERIC,
    i NUMERIC,
    j NUMERIC
);

-- Create occupations table
CREATE TABLE IF NOT EXISTS workers_comp.occupations (
    id SERIAL PRIMARY KEY,
    group_number INTEGER,
    occupation_title TEXT,
    industry TEXT
);

-- Create variants table
CREATE TABLE IF NOT EXISTS workers_comp.variants (
    id SERIAL PRIMARY KEY,
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
    group_290 TEXT,
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
CREATE TABLE IF NOT EXISTS workers_comp.age_adjustment (
    id SERIAL PRIMARY KEY,
    wpi_percent NUMERIC,
    "21_and_under" NUMERIC,
    "22_to_26" NUMERIC,
    "27_to_31" NUMERIC,
    "32_to_36" NUMERIC,
    "37_to_41" NUMERIC,
    "42_to_46" NUMERIC,
    "47_to_51" NUMERIC,
    "52_to_56" NUMERIC,
    "57_to_61" NUMERIC,
    "62_and_over" NUMERIC
);
