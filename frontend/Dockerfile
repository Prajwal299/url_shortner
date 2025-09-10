FROM nginx:1.29.1

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy website files
COPY index.html /usr/share/nginx/html/
COPY script.js /usr/share/nginx/html/

# Remove the corrupted script.jsO file if it exists
RUN rm -f /usr/share/nginx/html/script.jsO

# Set proper permissions
RUN chmod -R 755 /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Test configuration during build
RUN nginx -t

# Start nginx
CMD ["nginx", "-g", "daemon off;"]