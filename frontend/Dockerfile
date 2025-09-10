FROM nginx:1.29.1

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy your custom config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy website files
COPY index.html /usr/share/nginx/html/
COPY script.js /usr/share/nginx/html/
COPY custom.css /usr/share/nginx/html/

# Remove accidental extra files
RUN rm -f /usr/share/nginx/html/script.jsO

# Set permissions
RUN chmod -R 755 /usr/share/nginx/html

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
