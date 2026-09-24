-- Separate databases so neither test suite touches dev data, nor each other's rows.
CREATE DATABASE thiqa_test OWNER thiqa;
CREATE DATABASE thiqa_e2e OWNER thiqa;
