# Self hosted deployment

## Requirements
The self hosted connector runs as a Docker container. It needs 2 CPU cores, 4 GB of memory and outbound HTTPS access to api.clouddesk.example. Docker version 20 or newer is required.

## Configuration
Set the CLOUDDESK_API_KEY and CLOUDDESK_REGION environment variables. The container exposes a health endpoint at /healthz on port 8080. Logs are written to standard output in JSON format.

## Upgrades
Pull the new image tag and restart the container. The connector keeps no local state, so upgrades need no migration.
