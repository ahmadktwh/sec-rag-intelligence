# ── Build Stage ──────────────────────────────────────────────────────────────
FROM node:20-alpine as build-stage

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy project files and build
COPY . .
RUN npm run build

# ── Production Stage ─────────────────────────────────────────────────────────
FROM nginx:stable-alpine as production-stage

# Copy build artifacts to Nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy custom Nginx config if needed, otherwise default is fine
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
