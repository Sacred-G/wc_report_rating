CREATE TABLE occupational_data (
    id INT8 PRIMARY KEY,
    occupation TEXT,
    bodypart TEXT,
    age_injury DATE,
    wpi NUMERIC,
    adjusted_value NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes for commonly queried columns
CREATE INDEX idx_occupational_data_occupation ON occupational_data(occupation);
CREATE INDEX idx_occupational_data_bodypart ON occupational_data(bodypart);
CREATE INDEX idx_occupational_data_created_at ON occupational_data(created_at);
