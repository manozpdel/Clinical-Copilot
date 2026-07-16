FROM nginx:1.27-alpine

RUN adduser -D -u 1000 appuser

COPY deployment/nginx/nginx.conf /etc/nginx/nginx.conf

RUN touch /var/run/nginx.pid \
    && chown -R appuser:appuser /var/run/nginx.pid /var/cache/nginx /var/log/nginx

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost:8080/health || exit 1

CMD ["nginx", "-g", "daemon off;"]