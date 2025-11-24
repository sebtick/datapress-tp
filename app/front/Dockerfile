FROM nginx:alpine

# Supprime la config par défaut si besoin
RUN rm -rf /usr/share/nginx/html/*

COPY index.html /usr/share/nginx/html/index.html

EXPOSE 80
