# syntax=docker/dockerfile:1.7
# Imagen del proxy de Saber Uli (T009): compila la PWA y la sirve con Nginx sin root, junto con
# la redirección de /api/ y las cabeceras de seguridad (research R-33).
# Contexto de construcción: raíz del repositorio.

# ---------------------------------------------------------------------------------------------
# build: compila la PWA con Node 24.
# ---------------------------------------------------------------------------------------------
FROM node:24-alpine AS build
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------------------------
# runtime: Nginx sin privilegios (UID 101, puerto 8080).
# ---------------------------------------------------------------------------------------------
FROM nginxinc/nginx-unprivileged:1.29-alpine AS runtime

# Disposición descrita en infra/nginx/default.conf. En producción, compose.prod.yaml monta
# tls.conf sobre conf.d/default.conf.
COPY infra/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY infra/nginx/security-headers.conf infra/nginx/locations.conf infra/nginx/tls.conf \
     /etc/nginx/saber/
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 8080
