-- Create sequence for occupational_data table
CREATE SEQUENCE IF NOT EXISTS occupational_data_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Set the sequence owner to the id column
ALTER SEQUENCE occupational_data_id_seq OWNED BY occupational_data.id;

-- Set the default value for the id column
ALTER TABLE occupational_data ALTER COLUMN id SET DEFAULT nextval('occupational_data_id_seq');
