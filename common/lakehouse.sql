INSTALL httpfs;
INSTALL delta;

LOAD httpfs;
LOAD delta;

CREATE OR REPLACE SECRET seaweedfs (
    TYPE S3,
    KEY_ID 'cloudmetry-local-access',
    SECRET 'cloudmetry-local-secret-key-change-this',
    REGION 'us-east-1',
    ENDPOINT 'localhost:8333',
    URL_STYLE 'path',
    USE_SSL false
);


SELECT * FROM delta_scan('s3://silver/gps') LIMIT 100;
SELECT * FROM delta_scan('s3://silver/telemetry') LIMIT 2000;
SELECT * FROM delta_scan('s3://silver/accelerometer') LIMIT 100;
SELECT * FROM delta_scan('s3://gold/fct_drive_summary') LIMIT 100;