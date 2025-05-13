FROM nginx:alpine

WORKDIR /usr/share/nginx/html

# Copy all files from client directory to nginx html directory
COPY . .

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose the port nginx is running on
EXPOSE 80

# Start nginx in foreground
CMD ["nginx", "-g", "daemon off;"]