FROM redis:7.2

# Copy custom redis config
COPY redis.conf /usr/local/etc/redis/redis.conf

EXPOSE 6379

# Start Redis with the custom config
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
