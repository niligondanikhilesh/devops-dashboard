from flask import Flask, jsonify, request
from redis import Redis
from prometheus_client import Counter, Histogram, generate_latest
import time

app = Flask(__name__)
redis = Redis(host="redis", port=6379)

# Prometheus metrics
REQUEST_COUNT = Counter('app_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('app_request_latency_seconds', 'Request latency')
CACHE_HITS = Counter('app_cache_hits_total', 'Cache hits')
CACHE_MISSES = Counter('app_cache_misses_total', 'Cache misses')

@app.route("/")
def home():
    REQUEST_COUNT.labels(method='GET', endpoint='/').inc()
    return jsonify({"status": "DevOps Dashboard Running! 🚀"})

@app.route("/data/<key>")
def get_data(key):
    start = time.time()
    REQUEST_COUNT.labels(method='GET', endpoint='/data').inc()

    cached = redis.get(key)
    if cached:
        CACHE_HITS.inc()
        redis.incr("cache_hits")
        latency = time.time() - start
        REQUEST_LATENCY.observe(latency)
        return jsonify({"key": key, "value": cached.decode(), "source": "cache 🚀"})

    CACHE_MISSES.inc()
    redis.incr("cache_misses")
    value = f"generated-value-for-{key}"
    redis.set(key, value, ex=60)
    latency = time.time() - start
    REQUEST_LATENCY.observe(latency)
    return jsonify({"key": key, "value": value, "source": "generated 🔧"})

@app.route("/stats")
def stats():
    REQUEST_COUNT.labels(method='GET', endpoint='/stats').inc()
    hits = int(redis.get("cache_hits") or 0)
    misses = int(redis.get("cache_misses") or 0)
    total = hits + misses
    return jsonify({
        "cache_hits": hits,
        "cache_misses": misses,
        "total_requests": total,
        "hit_ratio": f"{round(hits/total*100)}%" if total > 0 else "0%"
    })

@app.route("/metrics")
def metrics():
    return generate_latest()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
