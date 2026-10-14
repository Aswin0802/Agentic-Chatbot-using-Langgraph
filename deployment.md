# PostgreSQL Setup on AWS EC2 for a Dockerized LangGraph Application

This document records the PostgreSQL setup sequence from my troubleshooting conversation. PostgreSQL was installed directly on the EC2 Ubuntu host, while the Streamlit/LangGraph application runs inside Docker.

> **Important:** The database password is intentionally not included. Use your own strong password and never commit credentials to GitHub.

## Architecture

- **EC2 host:** Ubuntu; PostgreSQL runs directly on the host.
- **Database:** `langgraph`
- **Database user:** `langgraph_app`
- **PostgreSQL port:** `5432`
- **Docker container:** `stapp`
- **Application port:** `8501`
- **Docker-to-host hostname:** `host.docker.internal`
- **GitHub Actions secret:** `DATABASE_URL`

---

## 1. Install PostgreSQL on EC2

Run these commands in the EC2 SSH terminal.

### Refresh Ubuntu package lists

```bash
sudo apt update
```

**Purpose:** Refreshes the package index so Ubuntu can find available packages.

### Install PostgreSQL and contributed extensions

```bash
sudo apt install -y postgresql postgresql-contrib
```

**Purpose:** Installs the PostgreSQL database server and contributed extensions.

### Start PostgreSQL and enable it after reboot

```bash
sudo systemctl enable --now postgresql
```

**Purpose:** Starts the service immediately and configures it to start automatically after an EC2 reboot.

### Check the service

```bash
sudo systemctl status postgresql --no-pager
```

**Purpose:** Displays the PostgreSQL service status. Depending on Ubuntu's service setup, the status can show `active (exited)` for the cluster-management service, so also test the database itself.

### Verify the server responds

```bash
sudo -u postgres psql -c "SELECT version();"
```

**Purpose:** Runs a query as the PostgreSQL administrator and prints the server version. During troubleshooting, this returned PostgreSQL version `18.6`.

---

## 2. Create the application database and user

### Open the PostgreSQL shell

```bash
sudo -u postgres psql
```

Run the following commands **one at a time** at the `postgres=#` prompt.

### Create the database

```sql
CREATE DATABASE langgraph;
```

**Purpose:** Creates the database for the application.

### Create the application login

```sql
CREATE USER langgraph_app WITH LOGIN;
```

**Purpose:** Creates a dedicated database user for the application rather than using the PostgreSQL administrator account.

### Grant database-level privileges

```sql
GRANT ALL PRIVILEGES ON DATABASE langgraph TO langgraph_app;
```

**Purpose:** Grants database-level privileges to `langgraph_app`.

### Set the user's password interactively

```sql
\password langgraph_app
```

**Purpose:** Prompts for the password twice without echoing it in the terminal. Keep the password private.

### Connect to the application database

```sql
\connect langgraph
```

**Purpose:** Switches the current `psql` session to the `langgraph` database.

### Grant schema permissions

```sql
GRANT USAGE, CREATE ON SCHEMA public TO langgraph_app;
```

**Purpose:** Allows the application user to use the `public` schema and create objects there. This may be needed for LangGraph checkpoint tables.

### Exit `psql`

```sql
\q
```

**Important lesson:** `\connect` is a `psql` meta-command, not SQL. Enter it on its own line, then run the `GRANT` statement separately. In the troubleshooting session, combining them caused an error; running them separately was the correction.

---

## 3. Configure PostgreSQL networking for Docker

The application runs inside Docker, but PostgreSQL runs on the EC2 host. The container must be allowed to connect to the host's PostgreSQL service.

### Set PostgreSQL to listen on network interfaces

```bash
sudo -u postgres psql -c "ALTER SYSTEM SET listen_addresses = '*';"
```

**Purpose:** Configures PostgreSQL to listen on all available network interfaces. This setting does not, by itself, authorize clients; `pg_hba.conf` and network security rules still control access.

### Find the PostgreSQL configuration file

```bash
sudo -u postgres psql -tAc "SHOW config_file;"
```

**Purpose:** Prints the active main configuration file path.

### Find the client authentication file

```bash
sudo -u postgres psql -tAc "SHOW hba_file;"
```

The command returned this path during setup:

```text
/etc/postgresql/18/main/pg_hba.conf
```

**Purpose:** Locates `pg_hba.conf`, which defines which clients can connect to which databases and users, and which authentication method they must use.

### Find the Docker bridge subnet

```bash
docker network inspect bridge --format '{{(index .IPAM.Config 0).Subnet}}'
```

The command returned:

```text
172.17.0.0/16
```

**Purpose:** Identifies the Docker bridge network's subnet. Use the value returned by your own instance if it differs.

### Add a PostgreSQL authentication rule

The command used during setup was:

```bash
echo "host langgraph langgraph_app 172.17.0.0/16 scram-sha-256" \
  | sudo tee -a /etc/postgresql/18/main/pg_hba.conf
```

**Purpose:** Allows TCP connections from the specified Docker subnet to database `langgraph` as user `langgraph_app`, using SCRAM-SHA-256 password authentication.

**Note:** The example uses the actual path and subnet recorded in the setup. If your configuration file path or Docker subnet differs, replace those values. Avoid appending duplicate rules if the rule is already present.

### Restart PostgreSQL

```bash
sudo systemctl restart postgresql
```

**Purpose:** Applies configuration changes, including `listen_addresses`.

### Verify the PostgreSQL listener

```bash
sudo ss -lntp | grep 5432
```

**Purpose:** Shows the interfaces listening on PostgreSQL's default port, `5432`.

**Security warning:** Do **not** open port `5432` to the public internet in the EC2 security group. Restrict access to the intended internal connection path.

---

## 4. Test the application database user locally

Run this from the normal Ubuntu shell, not from inside `psql`:

```bash
psql -h 127.0.0.1 -U langgraph_app -d langgraph
```

**Purpose:**
- `-h 127.0.0.1`: Connects over TCP to PostgreSQL on the EC2 host.
- `-U langgraph_app`: Uses the application database user.
- `-d langgraph`: Selects the `langgraph` database.

Enter the password when prompted. A successful connection should show a prompt similar to:

```text
langgraph=>
```

Optionally verify the current database and user:

```sql
SELECT current_database(), current_user;
```

Exit with:

```sql
\q
```

**What this test proves:** The user can authenticate and connect locally. It does not by itself prove that the Docker container can connect.

---

## 5. Allow the Docker container to reach the EC2 host

The container's `localhost` refers to the container itself, not the EC2 host. We used Docker's host-gateway mapping.

In the GitHub Actions workflow's `docker run` command, include:

```bash
--add-host=host.docker.internal:host-gateway
```

**Purpose:** Makes `host.docker.internal` resolve to the Docker host from inside the container on Linux.

---

## 6. Configure `DATABASE_URL` in GitHub Actions

In the GitHub repository, go to:

**Settings → Secrets and variables → Actions → New repository secret**

Create a secret named:

```text
DATABASE_URL
```

Its value should follow this format:

```text
postgresql://langgraph_app:YOUR_URL_ENCODED_PASSWORD@host.docker.internal:5432/langgraph
```

Replace `YOUR_URL_ENCODED_PASSWORD` with the password you set for `langgraph_app`. URL-encode special characters in the password when needed. Never put the real URL in source control or share it publicly.

### Pass the secret into the workflow step

In the relevant GitHub Actions step's `env:` section:

```yaml
DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

In the `docker run` command, pass it into the container:

```bash
-e DATABASE_URL
```

The exact placement and indentation depend on the workflow's existing YAML structure.

**Purpose:** GitHub Actions supplies the secret to the deployment step, and Docker passes it to the application container as an environment variable.

### Read the variable in Python

The application should read the URL from the environment instead of using a hardcoded localhost connection string:

```python
import os
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL is not configured")
```

This snippet reads the setting; the application's database/checkpoint code must actually use `database_url` to establish a connection.

For local development, a local `.env` file can contain a different `DATABASE_URL`. For deployment, the GitHub Actions secret supplies the container's runtime value.

---

## 7. Verification commands

These commands were collected in the troubleshooting conversation.

### Check Docker

```bash
docker --version
sudo systemctl status docker --no-pager
docker ps -a
```

**Purpose:** Check the Docker version, service status, and containers.

### Check PostgreSQL

```bash
psql --version
sudo systemctl status postgresql --no-pager
sudo -u postgres psql -c "SELECT version();"
sudo ss -lntp | grep 5432
```

**Purpose:** Check the PostgreSQL client version, service status, server response, and listening port.

### Check whether `DATABASE_URL` is present in the app container without revealing credentials

```bash
docker exec stapp python -c '
import os
from urllib.parse import urlparse

url = os.getenv("DATABASE_URL")
print("DATABASE_URL configured:", bool(url))
if url:
    parsed = urlparse(url)
    print("Database host:", parsed.hostname)
    print("Database port:", parsed.port)
    print("Database name:", parsed.path.lstrip("/"))
'
```

**Purpose:** Confirms whether the variable exists and displays non-secret connection details without printing the password.

---

## 8. What I learned from this setup

1. **Install the database server first.** Installing PostgreSQL on EC2 is separate from running the application in Docker.
2. **Create a dedicated database and login.** The app uses `langgraph` and `langgraph_app` rather than the PostgreSQL administrator account.
3. **Database privileges and schema privileges are distinct.** The database-level `GRANT` and the `public` schema `GRANT` address different permission scopes.
4. **PostgreSQL networking has multiple controls.** `listen_addresses` controls which interfaces PostgreSQL listens on; `pg_hba.conf` controls client authentication; the EC2 security group controls network reachability.
5. **Container localhost is not host localhost.** The container needs a host-gateway mapping to reach PostgreSQL running on the EC2 host.
6. **Secrets must be passed into the container.** Creating `DATABASE_URL` in GitHub is not enough unless the workflow passes it through to Docker and the Python application reads it.
7. **Verify each layer independently.** A successful PostgreSQL query, a successful local login, a Docker connection, and a successful application checkpoint operation test different parts of the setup.

## 9. Important distinction

The recorded setup shows PostgreSQL installation, database/user creation, configuration, and the intended Docker connection settings. A successful service check or local `psql` login does not alone prove that the deployed LangGraph application successfully uses PostgreSQL. Confirm that separately by checking the app's connection/checkpoint configuration and verifying a real database operation.

"""
path = Path("/mnt/data/postgresql_ec2_setup_reference.md")
path.write_text(content, encoding="utf-8")
print(f"Created: {path}")

from pathlib import Path

content = r"""# PostgreSQL Setup on AWS EC2 for a Dockerized LangGraph Application

This document records the PostgreSQL setup sequence from my troubleshooting conversation. PostgreSQL was installed directly on the EC2 Ubuntu host, while the Streamlit/LangGraph application runs inside Docker.

> **Important:** The database password is intentionally not included. Use your own strong password and never commit credentials to GitHub.

## Architecture

- **EC2 host:** Ubuntu; PostgreSQL runs directly on the host.
- **Database:** `langgraph`
- **Database user:** `langgraph_app`
- **PostgreSQL port:** `5432`
- **Docker container:** `stapp`
- **Application port:** `8501`
- **Docker-to-host hostname:** `host.docker.internal`
- **GitHub Actions secret:** `DATABASE_URL`

---

## 1. Install PostgreSQL on EC2

Run these commands in the EC2 SSH terminal.

### Refresh Ubuntu package lists

```bash
sudo apt update
```

**Purpose:** Refreshes the package index so Ubuntu can find available packages.

### Install PostgreSQL and contributed extensions

```bash
sudo apt install -y postgresql postgresql-contrib
```

**Purpose:** Installs the PostgreSQL database server and contributed extensions.

### Start PostgreSQL and enable it after reboot

```bash
sudo systemctl enable --now postgresql
```

**Purpose:** Starts the service immediately and configures it to start automatically after an EC2 reboot.

### Check the service

```bash
sudo systemctl status postgresql --no-pager
```

**Purpose:** Displays the PostgreSQL service status. Depending on Ubuntu's service setup, the status can show `active (exited)` for the cluster-management service, so also test the database itself.

### Verify the server responds

```bash
sudo -u postgres psql -c "SELECT version();"
```

**Purpose:** Runs a query as the PostgreSQL administrator and prints the server version. During troubleshooting, this returned PostgreSQL version `18.6`.

---

## 2. Create the application database and user

### Open the PostgreSQL shell

```bash
sudo -u postgres psql
```

Run the following commands **one at a time** at the `postgres=#` prompt.

### Create the database

```sql
CREATE DATABASE langgraph;
```

**Purpose:** Creates the database for the application.

### Create the application login

```sql
CREATE USER langgraph_app WITH LOGIN;
```

**Purpose:** Creates a dedicated database user for the application rather than using the PostgreSQL administrator account.

### Grant database-level privileges

```sql
GRANT ALL PRIVILEGES ON DATABASE langgraph TO langgraph_app;
```

**Purpose:** Grants database-level privileges to `langgraph_app`.

### Set the user's password interactively

```sql
\password langgraph_app
```

**Purpose:** Prompts for the password twice without echoing it in the terminal. Keep the password private.

### Connect to the application database

```sql
\connect langgraph
```

**Purpose:** Switches the current `psql` session to the `langgraph` database.

### Grant schema permissions

```sql
GRANT USAGE, CREATE ON SCHEMA public TO langgraph_app;
```

**Purpose:** Allows the application user to use the `public` schema and create objects there. This may be needed for LangGraph checkpoint tables.

### Exit `psql`

```sql
\q
```

**Important lesson:** `\connect` is a `psql` meta-command, not SQL. Enter it on its own line, then run the `GRANT` statement separately. In the troubleshooting session, combining them caused an error; running them separately was the correction.

---

## 3. Configure PostgreSQL networking for Docker

The application runs inside Docker, but PostgreSQL runs on the EC2 host. The container must be allowed to connect to the host's PostgreSQL service.

### Set PostgreSQL to listen on network interfaces

```bash
sudo -u postgres psql -c "ALTER SYSTEM SET listen_addresses = '*';"
```

**Purpose:** Configures PostgreSQL to listen on all available network interfaces. This setting does not, by itself, authorize clients; `pg_hba.conf` and network security rules still control access.

### Find the PostgreSQL configuration file

```bash
sudo -u postgres psql -tAc "SHOW config_file;"
```

**Purpose:** Prints the active main configuration file path.

### Find the client authentication file

```bash
sudo -u postgres psql -tAc "SHOW hba_file;"
```

The command returned this path during setup:

```text
/etc/postgresql/18/main/pg_hba.conf
```

**Purpose:** Locates `pg_hba.conf`, which defines which clients can connect to which databases and users, and which authentication method they must use.

### Find the Docker bridge subnet

```bash
docker network inspect bridge --format '{{(index .IPAM.Config 0).Subnet}}'
```

The command returned:

```text
172.17.0.0/16
```

**Purpose:** Identifies the Docker bridge network's subnet. Use the value returned by your own instance if it differs.

### Add a PostgreSQL authentication rule

The command used during setup was:

```bash
echo "host langgraph langgraph_app 172.17.0.0/16 scram-sha-256" \
  | sudo tee -a /etc/postgresql/18/main/pg_hba.conf
```

**Purpose:** Allows TCP connections from the specified Docker subnet to database `langgraph` as user `langgraph_app`, using SCRAM-SHA-256 password authentication.

**Note:** The example uses the actual path and subnet recorded in the setup. If your configuration file path or Docker subnet differs, replace those values. Avoid appending duplicate rules if the rule is already present.

### Restart PostgreSQL

```bash
sudo systemctl restart postgresql
```

**Purpose:** Applies configuration changes, including `listen_addresses`.

### Verify the PostgreSQL listener

```bash
sudo ss -lntp | grep 5432
```

**Purpose:** Shows the interfaces listening on PostgreSQL's default port, `5432`.

**Security warning:** Do **not** open port `5432` to the public internet in the EC2 security group. Restrict access to the intended internal connection path.

---

## 4. Test the application database user locally

Run this from the normal Ubuntu shell, not from inside `psql`:

```bash
psql -h 127.0.0.1 -U langgraph_app -d langgraph
```

**Purpose:**
- `-h 127.0.0.1`: Connects over TCP to PostgreSQL on the EC2 host.
- `-U langgraph_app`: Uses the application database user.
- `-d langgraph`: Selects the `langgraph` database.

Enter the password when prompted. A successful connection should show a prompt similar to:

```text
langgraph=>
```

Optionally verify the current database and user:

```sql
SELECT current_database(), current_user;
```

Exit with:

```sql
\q
```

**What this test proves:** The user can authenticate and connect locally. It does not by itself prove that the Docker container can connect.

---

## 5. Allow the Docker container to reach the EC2 host

The container's `localhost` refers to the container itself, not the EC2 host. We used Docker's host-gateway mapping.

In the GitHub Actions workflow's `docker run` command, include:

```bash
--add-host=host.docker.internal:host-gateway
```

**Purpose:** Makes `host.docker.internal` resolve to the Docker host from inside the container on Linux.

---

## 6. Configure `DATABASE_URL` in GitHub Actions

In the GitHub repository, go to:

**Settings → Secrets and variables → Actions → New repository secret**

Create a secret named:

```text
DATABASE_URL
```

Its value should follow this format:

```text
postgresql://langgraph_app:YOUR_URL_ENCODED_PASSWORD@host.docker.internal:5432/langgraph
```

Replace `YOUR_URL_ENCODED_PASSWORD` with the password you set for `langgraph_app`. URL-encode special characters in the password when needed. Never put the real URL in source control or share it publicly.

### Pass the secret into the workflow step

In the relevant GitHub Actions step's `env:` section:

```yaml
DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

In the `docker run` command, pass it into the container:

```bash
-e DATABASE_URL
```

The exact placement and indentation depend on the workflow's existing YAML structure.

**Purpose:** GitHub Actions supplies the secret to the deployment step, and Docker passes it to the application container as an environment variable.

### Read the variable in Python

The application should read the URL from the environment instead of using a hardcoded localhost connection string:

```python
import os
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL is not configured")
```

This snippet reads the setting; the application's database/checkpoint code must actually use `database_url` to establish a connection.

For local development, a local `.env` file can contain a different `DATABASE_URL`. For deployment, the GitHub Actions secret supplies the container's runtime value.

---

## 7. Verification commands

These commands were collected in the troubleshooting conversation.

### Check Docker

```bash
docker --version
sudo systemctl status docker --no-pager
docker ps -a
```

**Purpose:** Check the Docker version, service status, and containers.

### Check PostgreSQL

```bash
psql --version
sudo systemctl status postgresql --no-pager
sudo -u postgres psql -c "SELECT version();"
sudo ss -lntp | grep 5432
```

**Purpose:** Check the PostgreSQL client version, service status, server response, and listening port.

### Check whether `DATABASE_URL` is present in the app container without revealing credentials

```bash
docker exec stapp python -c '
import os
from urllib.parse import urlparse

url = os.getenv("DATABASE_URL")
print("DATABASE_URL configured:", bool(url))
if url:
    parsed = urlparse(url)
    print("Database host:", parsed.hostname)
    print("Database port:", parsed.port)
    print("Database name:", parsed.path.lstrip("/"))
'
```

**Purpose:** Confirms whether the variable exists and displays non-secret connection details without printing the password.

---

## 8. What I learned from this setup

1. **Install the database server first.** Installing PostgreSQL on EC2 is separate from running the application in Docker.
2. **Create a dedicated database and login.** The app uses `langgraph` and `langgraph_app` rather than the PostgreSQL administrator account.
3. **Database privileges and schema privileges are distinct.** The database-level `GRANT` and the `public` schema `GRANT` address different permission scopes.
4. **PostgreSQL networking has multiple controls.** `listen_addresses` controls which interfaces PostgreSQL listens on; `pg_hba.conf` controls client authentication; the EC2 security group controls network reachability.
5. **Container localhost is not host localhost.** The container needs a host-gateway mapping to reach PostgreSQL running on the EC2 host.
6. **Secrets must be passed into the container.** Creating `DATABASE_URL` in GitHub is not enough unless the workflow passes it through to Docker and the Python application reads it.
7. **Verify each layer independently.** A successful PostgreSQL query, a successful local login, a Docker connection, and a successful application checkpoint operation test different parts of the setup.

## 9. Important distinction

The recorded setup shows PostgreSQL installation, database/user creation, configuration, and the intended Docker connection settings. A successful service check or local `psql` login does not alone prove that the deployed LangGraph application successfully uses PostgreSQL. Confirm that separately by checking the app's connection/checkpoint configuration and verifying a real database operation.
"""
