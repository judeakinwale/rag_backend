# SSL Certificate

## Instructions

1. [Install mkcert](https://github.com/filosottile/mkcert#installation)

1. Ensure you are in the project root directory and have a terminal open at that directory

1. Navigate to the ./infrastructure/certs/ directory in the terminal

1. Create a certificate for localhost and the services using

    ``` sh
    mkcert localhost 127.0.0.1 ::1 ingest-service rag-service document-processor-service 
    ```

1. Rename the created certificate and certificate key using

    ```sh
    mv localhost+5.pem localhost.pem
    mv localhost+5-key.pem localhost-key.pem
    ```

1. Install the root CA in your system trust store using

    ```sh
    mkcert -install
    ```

1. Get the directory of mkcert's root certificate authority using

    ```sh
    mkcert --CAROOT
    ```

1. Ensure you are in the ./infrastructure/certs/ directory in the terminal before running the next command

1. Copy the root CA to the ./infrastructure/certs/ directory using

    ```sh
    cp $(mkcert --CAROOT)/rootCA.pem ./rootCA.pem
    cp $(mkcert --CAROOT)/rootCA-key.pem ./rootCA-key.pem
    ```

1. Return to the project root directory using

    ```sh
    cd ../..
    ```
<!-- - Place the ssl certificates in the ./certs/ directory before deployment
- Copy the root CA for verification into ./certs/
- update ROOT_CERT_PATH in service .env to /cert/rootCA.pem -->

### Certificate Overview

The created localhost.pem certificate is valid for the following domains:

- localhost
- 127.0.0.1
- ::1
- ingest-service
- rag-service
- document-processor-service
