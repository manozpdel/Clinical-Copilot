FROM nginx:1.27-alpine

RUN adduser -D -u 1000 appuser \
    && chown -R appuser:appuser /usr/share/nginx/html /var/cache/nginx /var/run \
    && touch /var/run/nginx.pid \
    && chown appuser:appuser /var/run/nginx.pid

COPY frontend /usr/share/nginx/html

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost:8080/index.html || exit 1

CMD ["nginx", "-g", "daemon off;"]