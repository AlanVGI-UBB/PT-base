#!/bin/sh
set -e

HOST=${CERT_HOST:-localhost}
CERT_DIR=/etc/nginx/certs
UPSTREAM=${BACKEND_UPSTREAM:-backend:8000}

mkdir -p /etc/nginx/conf.d
sed "s|\${BACKEND_UPSTREAM}|$UPSTREAM|g" /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

if [ ! -f "$CERT_DIR/cert.pem" ]; then
    mkdir -p "$CERT_DIR"

    SAN="DNS:localhost"
    case "$HOST" in
        *[!0-9.]*) ;;
        *) SAN="$SAN,IP:$HOST" ;;
    esac

    # --- Autoridad Certificadora (CA) ---
    openssl genrsa -out "$CERT_DIR/ca-key.pem" 2048 2>/dev/null
    openssl req -x509 -new -nodes -key "$CERT_DIR/ca-key.pem" \
        -subj "/CN=Puente LSCh Dev CA" \
        -days 3650 -out "$CERT_DIR/ca-cert.pem" 2>/dev/null

    # --- Certificado del servidor firmado por la CA ---
    openssl genrsa -out "$CERT_DIR/key.pem" 2048 2>/dev/null
    openssl req -new -key "$CERT_DIR/key.pem" \
        -subj "/CN=localhost" -out "$CERT_DIR/csr.pem" 2>/dev/null

    printf "subjectAltName=%s\n" "$SAN" > "$CERT_DIR/san.cnf"

    openssl x509 -req -in "$CERT_DIR/csr.pem" \
        -CA "$CERT_DIR/ca-cert.pem" -CAkey "$CERT_DIR/ca-key.pem" \
        -CAcreateserial -out "$CERT_DIR/cert.pem" \
        -days 365 -extfile "$CERT_DIR/san.cnf" 2>/dev/null

    # Copia pública de la CA para descarga desde el navegador
    cp "$CERT_DIR/ca-cert.pem" "/usr/share/nginx/html/ca.crt"

    echo "Certificados generados: CA + leaf cert (SAN: $SAN)"
fi

exec "$@"