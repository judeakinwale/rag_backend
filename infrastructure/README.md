# DMS - RAG Project

## Overview

This project is a document management system with retrieval-augmented generation features. Documents are sourced from SharePoint Document Libraries and processed into searchable vector embeddings. Users can interact with the documents through an AI chat interface.

- Frontend: React/SPFx SharePoint web part
- Backend: Python (three services)
- Storage: PostgreSQL + Qdrant (vector database)
- Source: SharePoint
- AI: OpenAI

## Architecture

```text
                         SharePoint
                             │
                             ▼
                    ┌─────────────────┐
                    │  Ingest Service │
                    └────────┬────────┘
                             │
                             ▼
                 ┌──────────────────────┐
                 │ Document Processor   │
                 └──────────┬───────────┘
                            │
                            ▼
                     Vector Database (Qdrant)
                            │
                            │ semantic search
                            ▼
┌──────────────┐     ┌──────────────┐
│ React / SPFx │ ──► │  RAG Service │
│  Frontend    │ ◄── │              │
└──────────────┘     └──────┬───────┘
                            │
                            ▼
                       OpenAI API
```

## Setting up the project

The project consists of two github repositories:

- Frontend: [KlafGO6-DMS](https://github.com/LummyP/KlafGO6-DMS)
- Backend: [rag_backend](https://github.com/LummyP/rag_backend)

<!-- They can be cloned into arbitrary folders but both need to be running at the same time -->

---

### Frontend

---

#### Frontend Prerequisites

- Node.js 22
- npm or Bun
- Access to a valid SharePoint organization account

*Recommendations:*

- *use nvm to manage Node.js installs. [nvm installation guide](https://www.freecodecamp.org/news/node-version-manager-nvm-install-guide/)*

---

#### Frontend Setup Steps

1. Clone the project from the [github repo](https://github.com/LummyP/KlafGO6-DMS)
<!-- (https://github.com/judeakinwale/dms-klafgo6).   -->

1. In the project root directory, open a terminal and install the dependencies using

    ```sh
    npm install
    # or
    bun install
    ```

1. For the first time running this application, run

    ```sh
    npm run init
    # or
    bun run init
    ```

1. Accept any prompts and when it is done running, stop the application using Control + c

1. Run the application using this command

    ```sh
    npm run serve
    # or
    bun run serve
    ```

### Backend

---

[Backend services details](#backend-services) and [API documentation](#api-documentation) can be found below.

#### Backend Prerequisites

- Docker Engine
- Docker Compose v2
- Python 3.13+ (local development only)
- UV (recommended for local Python environment)
- SharePoint credentials
- OpenAI API credentials

#### Docker

This requires Docker Engine and Docker Compose v2 +. installed and running.

1. Clone the project from the [github repo](https://github.com/LummyP/rag_backend)

1. From the project root, access the subfolders of the **infrastructure** and **services** folders,
rename the .env.example files to .env and update the configuration in them. [Environment variables setup guide](#environment-variables-setup)

    *Replace the postgres database configuration in the services .env files with that for an existing test database.  
    If one does not exist follow the steps in Local Development -> [Minimal Setup](#minimal-setup) below before continuing*

1. In the project root, open a terminal and run the containers for the first time using

    ```sh
    docker compose -f docker-compose.local.yml up --build -d
    ```

    ***Note: this takes a lot of time for the first build; approx 1 - 3 Hrs, as it setups the ML dependencies and downloads models***

1. For subsequent runs, the containers can be started using

    ```sh
    docker compose -f docker-compose.local.yml up -d
    ```

1. [Setup the local SSL certificates](#ssl-certificates-setup) for the services to run on https

1. Ensure you can access the following documentation url endpoints on the browser (this might require waiting for a few minutes)

    - RAG Service: <https://localhost:8003/docs>
    - Ingest Service: <https://localhost:8004/docs>
    - Document Processor Service: <https://localhost:8005/docs>

1. To force a rebuild of the images used for the containers, run

    ```sh
    docker compose -f docker-compose.local.yml build --no-cache
    ```

1. To stop the running containers, run

    ```sh
    docker compose -f docker-compose.local.yml down
    ```

#### Local Development

##### Minimal Setup

This requires Python 3.13 + to run.

Recommendations:

- install UV and install Python using [UV here](https://docs.astral.sh/uv/guides/install-python/)
- setup a [virtual environment](https://docs.astral.sh/uv/pip/environments/) and run the project in the virtual environment
- [activate the virtual environment](https://docs.astral.sh/uv/pip/environments/#using-a-virtual-environment) before following the steps below and before subsequent runs of the project

---

1. Clone the project from the [github repo](https://github.com/LummyP/rag_backend)

1. From the project root, access the subfolders of the **infrastructure** and **services** folders,
rename the .env.example files to .env and update the configuration in them. [Environment variables setup guide](#environment-variables-setup)

    *Replace the placeholder passwords and secrets as well as those in the database url and provide valid keys and ids for
    SharePoint and OpenAI in the .env files*

1. In the project root directory, open a terminal and install the dependencies using

    ```sh
    pip install -r ./requirements.txt
    ```

1. Run the setup scripts using:

    - for linux / mac os

        ```sh
        sh ./infrastructure/scripts/setup_project_migrations.sh
        ```

    - for windows

        ```sh
        bash ./infrastructure/scripts/setup_project_migrations.sh
        ```

##### Running Individual Services

Use this setup when developing or debugging an individual backend service. For normal local development, the Docker setup is recommended.

1. Follow the steps outlined in Local Development -> [Minimal Setup](#minimal-setup) above.

1. [Setup the local SSL certificates](#ssl-certificates-setup) for the services to run on HTTPS

1. To run a specific service:  

    - Open a terminal at the root directory of the service eg. at ./services/rag-service/

    - Install the dependencies required for that service using

        ```sh
        pip install -r ./requirements.txt
        ```

    - Update the ROOT_CERT_PATH in the .env file to the absolute path to ../../infrastructure/certs/rootCA.pem
        */certs/rootCA.pem is the accurate root cert path if the service is running in a container*

    - Run the service using

        ```sh
        python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --ssl-keyfile ../../infrastructure/certs/localhost-key.pem --ssl-certfile ../../infrastructure/certs/localhost.pem
        ```

        *The port should be of the form 80xx*

    - The API Documentation for the service can now be accessed at <https://host:port/docs> where from the above step,
    the host is 127.0.0.1 and the port is 8000 making <https://127.0.0.1:8000/docs> or <https://localhost:8000/docs>

1. To run multiple services, repeat the step above but use a unique 80xx port for each, eg. 8000, 8001, 8002 ...

1. To allow interactions between the multiple services over HTTPS, update the following .env configurations
in each service to match the host and port set for each service:

    - INGEST_SERVICE_ORIGIN

#### SSL Certificates Setup

##### Instructions

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

##### Certificate Overview

The created localhost.pem certificate is valid for the following domains:

- localhost
- 127.0.0.1
- ::1
- ingest-service
- rag-service
- document-processor-service

#### Environment Variables Setup

the .env.example files are located as shown below:
<!-- ├── redis/
│   └── .env.example -->

```text
infrastructure/
├── postgres/
│   └── .env.example
└── ...

services/
├── rag-service/
│   └── .env.example
├── ingest-service/
│   └── .env.example
└── document-processor-service/
    └── .env.example
```

They should be renamed to .env with the following variables updated with valid values in the .env files:

- PG_USER
- PG_PASSWORD
- PG_DB
<!--  -->
- PGADMIN_DEFAULT_EMAIL
- PGADMIN_DEFAULT_PASSWORD
<!--  -->
<!-- - REDIS_PASSWORD -->
<!--  -->
- DATABASE_URL  (if external database is used)
<!--  -->
- OPENAI_API_KEY
<!--  -->
<!-- - INGEST_SERVICE_ORIGIN
- ROOT_CERT_PATH -->
<!--  -->
- JWT_SECRET
<!--  -->
- AZURE_TENANT_ID
- AZURE_CLIENT_ID
- AZURE_CLIENT_SECRET
<!--  -->
- SHAREPOINT_SITE_URL
- SHAREPOINT_LIBRARY_IDS

## Running the Project

---

1. Ensure Docker is running.

1. Open a terminal at the root directory of the backend project and run:

    ```sh
    docker compose -f docker-compose.local.yml up -d
    ```

1. Ensure the local SSL certificate setup is done and the .env files are properly configured. [SSL certificates setup guide](#ssl-certificates-setup) and [Environment variables setup guide](#environment-variables-setup)

1. Ensure you can access the following documentation url endpoints on the browser (this might require waiting for a few minutes)

    - RAG Service: <https://localhost:8003/docs>
    - Ingest Service: <https://localhost:8004/docs>
    - Document Processor Service: <https://localhost:8005/docs>

1. Open a terminal at the root directory of the frontend project and run:

   ```sh
    npm run serve
    # or
    bun run serve
    ```

1. Ensure you're logged into a valid organization account for the frontend on your default browser

1. The frontend will launch on the browser when it is done loading

## Backend Services

---

The backend consists of 3 services:

- **RAG Service**: handling chat creation and management, fetching related context from the vector database and fetching the configured OpenAI model responses

- **Ingest Service**: handling polling the SharePoint Document Libraries, handing off new or updated documents to be processed and tracking active documents

- **Document processor Service**: handling the extraction of text from documents and vector indexing chunks of documents

Overview of the backend services and their default ports:

| Service            | Default Port | Documentation |
| ------------------ | -----------: | ------------- |
| RAG Service        |         8003 | `/docs`       |
| Ingest Service     |         8004 | `/docs`       |
| Document Processor |         8005 | `/docs`       |

## API Documentation

---

The API documentation for each service can be found at:

- **RAG Service**: <https://localhost:8003/docs>
- **Ingest Service**: <https://localhost:8004/docs>
- **Document processor Service**: <https://localhost:8005/docs>

## Workflows

---

The backend has 2 primary workflows described below.

### Document Ingest Workflow

1. The Ingest Service polls the configured document libraries every 5 minutes, fetching all documents whose created or modified timestamp is newer than the last polling check (created or modified since the last check).

    1. This process avoids duplicate documents by ensuring already created document entries are ignored unless they have been modified since their ingest

1. The Ingest Service creates entries for each new document and updates the existing entries for modified documents

1. The Ingest Service sends an event to the Document Processor Service to trigger the processing of each document, setting each document's ingest_status to started

    1. A force reprocess can be triggered using the POST endpoint <https://localhost:8004/api/v1/ingest/sharepoint> as shown in the [Ingest Service docs](https://localhost:8004/docs)

1. The Document Processor Service extracts the content of each document as text, creating chunks of the text which are then indexed and stored in a vector database

1. The Document Processor Service sends an event back to the Ingest Service letting it know the processing for a document has either completed or failed

1. The Ingest Service updates the document entry with the appropriate status depending on the completed or failed event received

### Chat Response Generation Workflow

1. The RAG Service receives an http request from the frontend to either create a new chat or update a chat with a new prompt

1. The RAG Service reviews the received prompt and hands it over to the configured OpenAI model along with any previous messages in the chat and some context if needed

    1. If the prompt requires context, the service does a semantic search on the indexed document chunks, getting a configurable number of vector documents that match or exceed a relevance threshold for the provided prompt.

1. The RAG Service receives the response from the configured OpenAI model, updates the chat's messages with the new message and sends the updated chat and messages to the frontend

<!-- ## Troubleshooting

---

## Deployment

### Backend Deployment

### Frontend Deployment -->
