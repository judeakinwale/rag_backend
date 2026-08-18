# DMS - RAG Project

## Setting up the project

---

### Frontend

---

This project requires Node.js 22 and npm to run.  

*Recommendations:*

- *use nvm to manage Node.js installs. [Guide here](https://www.freecodecamp.org/news/node-version-manager-nvm-install-guide/)*

---

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

#### Containers

This project requires Docker > v2 installed and running.

1. Clone the project from the [github repo](https://github.com/LummyP/rag_backend)

1. From the project root, access the subfolders of the **infrastructure** and **services** folders,
rename the .env.example files to .env and update the configuration in them to match.

    ***Replace the postgres database configuration in the services .env files with that for the live database.  
    If one does not exist follow the steps in Code (Minimal) below before continuing***

1. In the project root, open a terminal and run the containers using

    ```sh
    docker compose -f docker-compose.local.yml up --build -d
    ```

    ***Note: this takes a lot of time; approx 1 - 3 Hrs***

1. Install the local root certificate located at **./infrastructure/certs/rootCA.pem** :

    - [install mkcert](https://github.com/filosottile/mkcert#installation)
    - [install the CA on your machine](https://github.com/filosottile/mkcert#changing-the-location-of-the-ca-files)
    - install the CA on your browser

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
    docker compose -f docker-compose.local.yml up --build -d
    ```

#### Code (Minimal)

This project requires Python >= 3.13 to run.

Recommendations:

- install UV and install Python using [UV here](https://docs.astral.sh/uv/guides/install-python/)
- setup a [virtual environment](https://docs.astral.sh/uv/pip/environments/) and run the project in the virtual environment
- [activate the virtual environment](https://docs.astral.sh/uv/pip/environments/#using-a-virtual-environment) before following the steps below and before subsequent runs of the project

---

1. Clone the project from the [github repo](https://github.com/LummyP/rag_backend)

1. From the project root, access the subfolders of the **infrastructure** and **services** folders,
rename the .env.example files to .env and update the configuration in them to match.

    ***Replace the placeholder passwords and secrets as well as those in the database url and provide valid keys and ids for
    SharePoint and OpenAI in the .env files***

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

#### Code (Full)

1. Follow the steps outlined in Code (Mininal) above.

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
        python -m uvicorn app.main:app
        --host 127.0.0.1 --port 8000 --reload
        --ssl-keyfile ../../infrastructure/certs/localhost+3-key.pem
        --ssl-certfile ../../infrastructure/certs/localhost+3.pem
        ```

        *The port should be of the form 80xx*

    - The API Documentation for the service can now be accessed at <https://host:port> where from the above step,
    the host is 127.0.0.1 and the port is 8000

1. To run multiple services, repeat the step above but use a unique 80xx port for each, eg. 8000, 8001, 8002 ...

1. To allow interactions between the multiple services over http, update the following .env configurations
in each service to match the host and port set for each service:

    - INGEST_SERVICE_ORIGIN

## Running the Project

---

1. Ensure Docker is running.

1. Open a terminal at the root directory of the backend project and run:

    ```sh
    docker compose -f docker-compose.local.yml up --build -d
    ```

1. Ensure the local root certificate is installed in either or both your machine and default browser  
    *see Project Setup -> Backend -> Containers*

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
