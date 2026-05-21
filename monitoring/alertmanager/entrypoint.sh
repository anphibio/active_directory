#!/bin/sh
set -eu

CONFIG_FILE=${ALERTMANAGER_CONFIG_FILE:-/tmp/alertmanager-$$.yml}
DEFAULT_RECEIVER=default
CORPORATE_RECEIVER=corporate
ACTIVE_RECEIVER=$DEFAULT_RECEIVER

bool_enabled() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

yaml_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

if bool_enabled "${ALERTMANAGER_WEBHOOK_ENABLED:-false}" && [ -n "${ALERTMANAGER_WEBHOOK_URL:-}" ]; then
  ACTIVE_RECEIVER=$CORPORATE_RECEIVER
fi

if bool_enabled "${ALERTMANAGER_SMTP_ENABLED:-false}" && [ -n "${ALERTMANAGER_SMTP_TO:-}" ]; then
  ACTIVE_RECEIVER=$CORPORATE_RECEIVER
fi

cat > "$CONFIG_FILE" <<EOF
global:
  resolve_timeout: ${ALERTMANAGER_RESOLVE_TIMEOUT:-5m}
EOF

if bool_enabled "${ALERTMANAGER_SMTP_ENABLED:-false}" && [ -n "${ALERTMANAGER_SMTP_SMARTHOST:-}" ]; then
  cat >> "$CONFIG_FILE" <<EOF
  smtp_smarthost: "$(yaml_escape "$ALERTMANAGER_SMTP_SMARTHOST")"
  smtp_from: "$(yaml_escape "${ALERTMANAGER_SMTP_FROM:-admanager@example.local}")"
EOF
  if [ -n "${ALERTMANAGER_SMTP_AUTH_USERNAME:-}" ]; then
    cat >> "$CONFIG_FILE" <<EOF
  smtp_auth_username: "$(yaml_escape "$ALERTMANAGER_SMTP_AUTH_USERNAME")"
EOF
  fi
  if [ -n "${ALERTMANAGER_SMTP_AUTH_PASSWORD:-}" ]; then
    cat >> "$CONFIG_FILE" <<EOF
  smtp_auth_password: "$(yaml_escape "$ALERTMANAGER_SMTP_AUTH_PASSWORD")"
EOF
  fi
  if [ -n "${ALERTMANAGER_SMTP_AUTH_IDENTITY:-}" ]; then
    cat >> "$CONFIG_FILE" <<EOF
  smtp_auth_identity: "$(yaml_escape "$ALERTMANAGER_SMTP_AUTH_IDENTITY")"
EOF
  fi
  if [ -n "${ALERTMANAGER_SMTP_REQUIRE_TLS:-}" ]; then
    cat >> "$CONFIG_FILE" <<EOF
  smtp_require_tls: ${ALERTMANAGER_SMTP_REQUIRE_TLS}
EOF
  fi
fi

cat >> "$CONFIG_FILE" <<EOF

templates:
  - /etc/alertmanager/templates/*.tmpl

route:
  receiver: ${ACTIVE_RECEIVER}
  group_by:
    - alertname
    - severity
    - environment
  group_wait: ${ALERTMANAGER_GROUP_WAIT:-30s}
  group_interval: ${ALERTMANAGER_GROUP_INTERVAL:-5m}
  repeat_interval: ${ALERTMANAGER_REPEAT_INTERVAL:-4h}
  routes:
    - matchers:
        - severity="critical"
      receiver: ${ACTIVE_RECEIVER}
      repeat_interval: ${ALERTMANAGER_CRITICAL_REPEAT_INTERVAL:-1h}

receivers:
  - name: ${DEFAULT_RECEIVER}
EOF

if [ "$ACTIVE_RECEIVER" = "$CORPORATE_RECEIVER" ]; then
  cat >> "$CONFIG_FILE" <<EOF
  - name: ${CORPORATE_RECEIVER}
EOF

  if bool_enabled "${ALERTMANAGER_WEBHOOK_ENABLED:-false}" && [ -n "${ALERTMANAGER_WEBHOOK_URL:-}" ]; then
    cat >> "$CONFIG_FILE" <<EOF
    webhook_configs:
      - url: "$(yaml_escape "$ALERTMANAGER_WEBHOOK_URL")"
        send_resolved: ${ALERTMANAGER_WEBHOOK_SEND_RESOLVED:-true}
EOF
  fi

  if bool_enabled "${ALERTMANAGER_SMTP_ENABLED:-false}" && [ -n "${ALERTMANAGER_SMTP_TO:-}" ]; then
    cat >> "$CONFIG_FILE" <<EOF
    email_configs:
      - to: "$(yaml_escape "$ALERTMANAGER_SMTP_TO")"
        send_resolved: ${ALERTMANAGER_EMAIL_SEND_RESOLVED:-true}
        headers:
          subject: '{{ template "admanager.email.subject" . }}'
        html: '{{ template "admanager.email.html" . }}'
EOF
  fi
fi

if bool_enabled "${ALERTMANAGER_VALIDATE_CONFIG_ONLY:-false}"; then
  cat "$CONFIG_FILE"
  exit 0
fi

exec /bin/alertmanager \
  --config.file="$CONFIG_FILE" \
  --storage.path=/alertmanager
