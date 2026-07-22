#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
target="$repo_root/.env"
if [ -e "$target" ]; then
  echo ".env already exists. Back it up or remove it before generating a new configuration." >&2
  exit 1
fi

secret() {
  openssl rand -base64 "$1" | tr '+/' '-_' | tr -d '=\n'
}

postgres_password=$(secret 24)
rabbit_password=$(secret 24)
minio_password=$(secret 24)
runner_token=$(secret 32)
auth_secret=$(secret 48)
admin_password=$(secret 18)

sed \
  -e "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$postgres_password|" \
  -e "s|RABBITMQ_DEFAULT_PASS=.*|RABBITMQ_DEFAULT_PASS=$rabbit_password|" \
  -e "s|MINIO_ROOT_PASSWORD=.*|MINIO_ROOT_PASSWORD=$minio_password|" \
  -e "s|LLMAPT_DATABASE_URL=.*|LLMAPT_DATABASE_URL=postgresql+asyncpg://llmapt:$postgres_password@postgres:5432/llmapt|" \
  -e "s|LLMAPT_BROKER_URL=.*|LLMAPT_BROKER_URL=amqp://llmapt:$rabbit_password@rabbitmq:5672//|" \
  -e "s|LLMAPT_RUNNER_TOKEN=.*|LLMAPT_RUNNER_TOKEN=$runner_token|" \
  -e "s|LLMAPT_AUTH_SECRET=.*|LLMAPT_AUTH_SECRET=$auth_secret|" \
  -e "s|LLMAPT_BOOTSTRAP_ADMIN_PASSWORD=.*|LLMAPT_BOOTSTRAP_ADMIN_PASSWORD=$admin_password|" \
  "$repo_root/.env.example" > "$target"
chmod 600 "$target"
echo "Created $target"
echo "Administrator password is stored in .env (LLMAPT_BOOTSTRAP_ADMIN_PASSWORD)."
echo "Do not commit or share the .env file."
