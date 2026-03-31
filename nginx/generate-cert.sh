#!/bin/bash
set -e
CERT_DIR="/etc/nginx/certs"
mkdir -p "$CERT_DIR"
if [ ! -f "$CERT_DIR/selfsigned.crt" ]; then
    openssl req -x509 -nodes -days 365 \
        -newkey rsa:2048 \
        -keyout "$CERT_DIR/selfsigned.key" \
        -out "$CERT_DIR/selfsigned.crt" \
        -subj "/CN=smarthr/O=SmartHR/C=CN"
    echo "Self-signed certificate generated."
else
    echo "Certificate already exists, skipping."
fi
