# Kiizama - Deployment

You can deploy the project using Docker Compose to a remote server.

This project expects you to have a Traefik proxy handling communication to the outside world and HTTPS certificates.

You can deploy with Docker Compose on your own server, or use Render with the included `render.yaml`.

CI is handled with GitHub Actions workflows in `.github/workflows`.

But you have to configure a couple things first. 🤓

## Preparation

* Have a remote server ready and available.
* Configure the DNS records of your domain to point to the IP of the server you just created.
* Configure a wildcard subdomain for your domain, so that you can have multiple subdomains for different services, e.g. `*.kiizama.example.com`. This will be useful for accessing different components, like `app.kiizama.example.com`, `api.kiizama.example.com`, `traefik.kiizama.example.com`, etc. And also for `staging`, like `app.staging.kiizama.example.com`, etc.
* Install and configure [Docker](https://docs.docker.com/engine/install/) on the remote server (Docker Engine, not Docker Desktop).

## Public Traefik

We need a Traefik proxy to handle incoming connections and HTTPS certificates.

You need to do these next steps only once.

### Traefik Docker Compose

* Create a remote directory to store your Traefik Docker Compose file:

```bash
mkdir -p /root/code/traefik-public/
```

Copy the Traefik Docker Compose file to your server. You could do it by running the command `rsync` in your local terminal:

```bash
rsync -a docker-compose.traefik.yml root@your-server.example.com:/root/code/traefik-public/
```

### Traefik Public Network

This Traefik will expect a Docker "public network" named `traefik-public` to communicate with your stack(s).

This way, there will be a single public Traefik proxy that handles the communication (HTTP and HTTPS) with the outside world, and then behind that, you could have one or more stacks with different domains, even if they are on the same single server.

To create a Docker "public network" named `traefik-public` run the following command in your remote server:

```bash
docker network create traefik-public
```

### Traefik Environment Variables

The Traefik Docker Compose file expects some environment variables to be set in your terminal before starting it. You can do it by running the following commands in your remote server.

* Create the username for HTTP Basic Auth, e.g.:

```bash
export USERNAME=admin
```

* Create an environment variable with the password for HTTP Basic Auth, e.g.:

```bash
export PASSWORD=changethis
```

* Use openssl to generate the "hashed" version of the password for HTTP Basic Auth and store it in an environment variable:

```bash
export HASHED_PASSWORD=$(openssl passwd -apr1 $PASSWORD)
```

To verify that the hashed password is correct, you can print it:

```bash
echo $HASHED_PASSWORD
```

* Create an environment variable with the domain name for your server, e.g.:

```bash
export DOMAIN=kiizama.example.com
```

* Create an environment variable with the email for Let's Encrypt, e.g.:

```bash
export EMAIL=admin@example.com
```

**Note**: you need to set a different email, an email `@example.com` won't work.

### Start the Traefik Docker Compose

Go to the directory where you copied the Traefik Docker Compose file in your remote server:

```bash
cd /root/code/traefik-public/
```

Now with the environment variables set and the `docker-compose.traefik.yml` in place, you can start the Traefik Docker Compose running the following command:

```bash
docker compose -f docker-compose.traefik.yml up -d
```

## Deploy Kiizama

Now that you have Traefik in place you can deploy Kiizama with Docker Compose.

**Note**: If you use Render, jump to the section about Continuous Deployment (CD).

## Environment Variables

You need to set some environment variables first.

Set the `ENVIRONMENT`, by default `local` (for development), but when deploying to a server you would put something like `staging` or `production`:

```bash
export ENVIRONMENT=production
```

Set the `DOMAIN`, by default `localhost` (for development), but when deploying you would use your own domain, for example:

```bash
export DOMAIN=kiizama.example.com
```

You can set several variables, like:

* `PROJECT_NAME`: The name of the project, used in the API for the docs and emails.
* `STACK_NAME`: The name of the stack used for Docker Compose labels and project name, this should be different for `staging`, `production`, etc. You could use the same domain replacing dots with dashes, e.g. `kiizama-example-com` and `staging-kiizama-example-com`.
* `FRONTEND_HOST`: Canonical authenticated app URL used by backend-generated links in emails.
* `BACKEND_CORS_ORIGINS`: A list of allowed CORS origins separated by commas.
* `SECRET_KEY`: The secret key for Kiizama, used to sign tokens.
* `SECRET_KEY_IG_CREDENTIALS`: Secret used for Instagram credentials encryption/decryption.
* `FIRST_SUPERUSER`: The email of the first superuser, this superuser will be the one that can create new users.
* `FIRST_SUPERUSER_PASSWORD`: The password of the first superuser.
* `SYSTEM_ADMIN_EMAIL` / `SYSTEM_ADMIN_PASSWORD`: Optional internal system admin credentials.
* `SMTP_HOST`: The SMTP server host to send emails, this would come from your email provider (E.g. Mailgun, Sparkpost, Sendgrid, etc).
* `SMTP_USER`: The SMTP server user to send emails.
* `SMTP_PASSWORD`: The SMTP server password to send emails.
* `EMAILS_FROM_EMAIL`: The email account to send emails from.
* `DATABASE_URL_PRODUCTION_INTERNAL`: Database URL used for `production`.
* `DATABASE_URL`: Generic database URL used outside production unless a production-specific one is set.
* `POSTGRES_SERVER` / `POSTGRES_PORT` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`: Legacy fallback if URL vars are not set.
* `MONGODB_URL`: MongoDB connection URL used by API services.
* `MONGODB_KIIZAMA_IG`: MongoDB database name (default `kiizama_ig`).
* `OPENAI_API_KEY`: OpenAI API key for AI enrichment flows.
* `REPUTATION_OPENAI_TIMEOUT_SECONDS`: Timeout for OpenAI reputation analysis calls.
* `REPUTATION_OPENAI_MAX_RETRIES`: Retry count for OpenAI reputation analysis calls.
* `SENTRY_DSN`: The DSN for Sentry, if you are using it.
* `DOCKER_IMAGE_BACKEND` / `DOCKER_IMAGE_FRONTEND`: Optional Docker image names/tags for Compose deploys.
* `IG_SCRAPE_WORKER_ID`: Optional explicit worker identity used for lease ownership.
* `IG_SCRAPE_WORKER_POLL_SECONDS`: Poll interval for queued/stale jobs.
* `IG_SCRAPE_WORKER_HEARTBEAT_SECONDS`: Heartbeat interval while processing a job.
* `IG_SCRAPE_WORKER_LEASE_SECONDS`: Lease duration for running jobs before stale recovery.
* `IG_SCRAPE_WORKER_MAX_ATTEMPTS`: Maximum attempts before a job is marked failed.
* `IG_SCRAPE_WORKER_ERROR_MAX_LEN`: Max persisted error length.

## Async Scrape Worker Process

For asynchronous Instagram jobs, run a separate worker process in addition to the API service (for host-based deployments with repository checkout):

```bash
backend/.venv/bin/python -m scrape_worker.main
```

This worker consumes `ig_scrape_jobs` documents, performs scraping + AI enrichment + persistence, and updates job status (`queued`, `running`, `done`, `failed`).

### Render Background Worker (Docker)

This repository now includes:

* `Dockerfile.worker`: Playwright-based worker image
* `render.yaml`: Render service definition for the background worker

To deploy on Render:

1. Create a Background Worker service from this repository.
2. Use Docker runtime with:
   * Dockerfile path: `./Dockerfile.worker`
   * Docker context: `.`
   * Start command: `python -m scrape_worker.main` (already set in `render.yaml`)
3. Attach the same environment variables used by backend (recommended via an Environment Group), plus worker tuning vars.

Important: the worker now has dedicated config keys and no longer requires the full backend settings set. At minimum ensure these are present:

* `IG_SCRAPE_WORKER_MONGODB_URL`
* `IG_SCRAPE_WORKER_SECRET_KEY_IG_CREDENTIALS`
* `IG_SCRAPE_WORKER_OPENAI_API_KEY`

Optional (defaults exist):

* `IG_SCRAPE_WORKER_MONGODB_KIIZAMA_IG` (default `kiizama_ig`)

Worker-specific vars (optional, defaults exist):

* `IG_SCRAPE_WORKER_ID`
* `IG_SCRAPE_WORKER_POLL_SECONDS`
* `IG_SCRAPE_WORKER_HEARTBEAT_SECONDS`
* `IG_SCRAPE_WORKER_LEASE_SECONDS`
* `IG_SCRAPE_WORKER_MAX_ATTEMPTS`
* `IG_SCRAPE_WORKER_ERROR_MAX_LEN`

Fallback compatibility:

* If the worker-prefixed vars are not provided, the worker can still read shared keys:
  * `MONGODB_URL`
  * `MONGODB_KIIZAMA_IG`
  * `SECRET_KEY_IG_CREDENTIALS`
  * `OPENAI_API_KEY`

## GitHub Actions Secrets

These repository secrets are used by the current GitHub Actions workflows:

* `SMOKESHOW_AUTH_KEY`: Auth key used by [Smokeshow](https://github.com/samuelcolvin/smokeshow) to publish coverage reports.

`GITHUB_TOKEN` is provided by GitHub Actions automatically.

## Generate secret keys

Some environment variables in the `.env` file have insecure placeholder values such as `changethis` or `ChangeThis1!`.

You have to change them with a secret key, to generate secret keys you can run the following command:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the content and use that as password / secret key. And run that again to generate another secure key.

## Deploy with Docker Compose

With the environment variables in place, you can deploy with Docker Compose:

```bash
docker compose -f docker-compose.yml up -d
```

For production you wouldn't want to have the overrides in `docker-compose.override.yml`, that's why we explicitly specify `docker-compose.yml` as the file to use.

## Continuous Deployment (CD)

This repository currently uses Render for automatic deployments through `render.yaml`.

The services in `render.yaml` are configured with `autoDeploy: true`, so Render deploys automatically when changes are pushed to the connected branch (typically `main`).

### Render Setup

1. Connect this repository in Render.
2. Create services from `render.yaml` (Blueprint), or mirror the same service settings manually.
3. Set required environment variables/secrets for each service.
4. Verify each service branch is set to `main` (or your target branch).

### GitHub Actions and CD

There are no GitHub Actions deployment workflows in this repository right now.

GitHub Actions are currently used for CI, testing, labeling, conflict detection, and coverage reporting.

## URLs

Replace `kiizama.example.com` with your domain.

### Main Traefik Dashboard

Traefik UI: `https://traefik.kiizama.example.com`

### Production

Frontend: `https://app.kiizama.example.com`

Backend API docs: `https://api.kiizama.example.com/docs`

Backend API base URL: `https://api.kiizama.example.com`

### Staging

Frontend: `https://app.staging.kiizama.example.com`

Backend API docs: `https://api.staging.kiizama.example.com/docs`

Backend API base URL: `https://api.staging.kiizama.example.com`
