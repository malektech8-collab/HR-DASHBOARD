# Stage 1: Build the Vite static assets
FROM node:22-alpine AS builder

WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json ./

# Install dependencies using clean install
RUN npm ci

# Copy the rest of the frontend source code
COPY . .

# Build-time argument for API URL integration
ARG VITE_API_URL=http://localhost:8080
ENV VITE_API_URL=${VITE_API_URL}

# Compile static distribution assets
RUN npm run build

# Stage 2: Serve compiled dist folder with Nginx Alpine (rootless config)
FROM nginx:alpine

# Copy custom Nginx virtual host configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build output to Nginx document root
COPY --from=builder /app/dist /usr/share/nginx/html

# Establish unprivileged runtime permissions
RUN touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx/conf.d

# Switch to the pre-existing unprivileged nginx user
USER nginx

# Expose HTTP proxy port
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
