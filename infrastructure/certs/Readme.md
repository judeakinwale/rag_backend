# SSL Certificate

## Instructions

- Place the ssl certificates in the ./certs/ directory before deployment
- Copy the root CA for verification into ./certs/
- update ROOT_CERT_PATH in service .env to /cert/rootCA.pem

### Certificates

localhost+3.pem is valid for

- localhost
- 127.0.0.1
- ::1
- ingest-service
