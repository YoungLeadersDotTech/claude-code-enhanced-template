#!/usr/bin/env python3
"""
Resilient API client with rate limiting, retry logic, and circuit breaker
"""

import time
import random
import hashlib
import json
import os
from typing import Optional, Dict, Any, Callable, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import threading
from collections import deque
from functools import wraps
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from exporter_config import ExporterConfig, RetryConfig, RateLimitConfig, CircuitBreakerConfig


class RateLimiter:
    """Token bucket rate limiter with burst support"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = config.burst_size
        self.max_tokens = config.burst_size
        self.refill_rate = config.requests_per_second
        self.last_refill = time.time()
        self.lock = threading.Lock()
        
    def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens from the bucket. Returns the time to wait.
        """
        with self.lock:
            now = time.time()
            
            # Refill tokens based on time elapsed
            time_elapsed = now - self.last_refill
            tokens_to_add = time_elapsed * self.refill_rate
            self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0  # No wait needed
            else:
                # Calculate wait time
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.refill_rate
                wait_time = max(wait_time, self.config.min_request_interval)
                return wait_time


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    class State:
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = self.State.CLOSED
        self.lock = threading.Lock()
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with circuit breaker protection"""
        with self.lock:
            if self.state == self.State.OPEN:
                if self._should_attempt_reset():
                    self.state = self.State.HALF_OPEN
                else:
                    raise Exception("Circuit breaker is OPEN")
                    
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
            
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        return (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.config.recovery_timeout)
                
    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            self.failure_count = 0
            self.state = self.State.CLOSED
            
    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.config.failure_threshold:
                self.state = self.State.OPEN


class RequestCache:
    """Simple request cache with TTL support"""
    
    def __init__(self, cache_dir: str, ttl: int, max_size: int):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.max_size = max_size
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_index = self._load_index()
        self.lock = threading.Lock()
        
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load cache index from disk"""
        index_file = self.cache_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
        
    def _save_index(self):
        """Save cache index to disk"""
        index_file = self.cache_dir / "index.json"
        with open(index_file, 'w') as f:
            json.dump(self.cache_index, f)
            
    def _get_cache_key(self, method: str, url: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from request parameters"""
        cache_data = f"{method}:{url}"
        if params:
            cache_data += ":" + json.dumps(params, sort_keys=True)
        return hashlib.md5(cache_data.encode()).hexdigest()
        
    def get(self, method: str, url: str, params: Optional[Dict] = None) -> Optional[Any]:
        """Get cached response if available and not expired"""
        with self.lock:
            cache_key = self._get_cache_key(method, url, params)
            
            if cache_key in self.cache_index:
                entry = self.cache_index[cache_key]
                if time.time() - entry['timestamp'] < self.ttl:
                    cache_file = self.cache_dir / f"{cache_key}.json"
                    if cache_file.exists():
                        try:
                            with open(cache_file, 'r') as f:
                                return json.load(f)
                        except:
                            pass
                            
                # Remove expired entry
                del self.cache_index[cache_key]
                self._save_index()
                
        return None
        
    def set(self, method: str, url: str, response: Any, params: Optional[Dict] = None):
        """Cache a response"""
        with self.lock:
            cache_key = self._get_cache_key(method, url, params)
            
            # Enforce max size
            if len(self.cache_index) >= self.max_size:
                # Remove oldest entry
                oldest_key = min(self.cache_index.keys(), 
                               key=lambda k: self.cache_index[k]['timestamp'])
                del self.cache_index[oldest_key]
                (self.cache_dir / f"{oldest_key}.json").unlink(missing_ok=True)
                
            # Save response
            cache_file = self.cache_dir / f"{cache_key}.json"
            with open(cache_file, 'w') as f:
                json.dump(response, f)
                
            # Update index
            self.cache_index[cache_key] = {
                'timestamp': time.time(),
                'url': url,
                'method': method
            }
            self._save_index()


class ResilientAPIClient:
    """API client with retry logic, rate limiting, and circuit breaker"""
    
    def __init__(self, config: ExporterConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize components
        self.rate_limiter = RateLimiter(config.rate_limit)
        self.circuit_breaker = CircuitBreaker(config.circuit_breaker)
        
        # Initialize cache if enabled
        self.cache = None
        if config.cache.enabled:
            self.cache = RequestCache(
                config.cache.cache_dir,
                config.cache.ttl,
                config.cache.max_size
            )
            
        # Create session with retry adapter
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry configuration"""
        session = requests.Session()
        
        # Configure retries at the transport level
        retry_strategy = Retry(
            total=self.config.retry.max_retries,
            status_forcelist=self.config.retry.retry_on_status_codes,
            method_whitelist=["GET", "POST", "PUT", "DELETE"],
            backoff_factor=self.config.retry.exponential_base,
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
        
    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter"""
        delay = min(
            self.config.retry.initial_delay * (self.config.retry.exponential_base ** attempt),
            self.config.retry.max_delay
        )
        
        if self.config.retry.jitter:
            # Add random jitter (±25%)
            jitter = delay * 0.25 * (2 * random.random() - 1)
            delay += jitter
            
        return max(0, delay)
        
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make a single request with timeout configuration"""
        timeout = (self.config.timeout.connect_timeout, self.config.timeout.read_timeout)
        kwargs['timeout'] = kwargs.get('timeout', timeout)
        
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response
        
    def request(self, method: str, url: str, use_cache: bool = True, **kwargs) -> requests.Response:
        """
        Make a resilient API request with retry logic, rate limiting, and circuit breaker
        """
        # Check cache first
        if use_cache and self.cache and method.upper() == "GET":
            cached_response = self.cache.get(method, url, kwargs.get('params'))
            if cached_response is not None:
                self.logger.debug(f"Cache hit for {url}")
                # Create a mock response object
                response = requests.Response()
                response.status_code = 200
                response._content = json.dumps(cached_response).encode('utf-8')
                response.headers['Content-Type'] = 'application/json'
                return response
                
        # Apply rate limiting
        wait_time = self.rate_limiter.acquire()
        if wait_time > 0:
            self.logger.debug(f"Rate limit: waiting {wait_time:.2f}s before request")
            time.sleep(wait_time)
            
        # Attempt request with retries
        last_exception = None
        for attempt in range(self.config.retry.max_retries + 1):
            try:
                # Use circuit breaker
                response = self.circuit_breaker.call(
                    self._make_request, method, url, **kwargs
                )
                
                # Cache successful GET responses
                if use_cache and self.cache and method.upper() == "GET" and response.ok:
                    try:
                        self.cache.set(method, url, response.json(), kwargs.get('params'))
                    except:
                        pass  # Ignore cache errors
                        
                return response
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                
                # Check if we should retry
                if attempt < self.config.retry.max_retries:
                    # Check if it's a retryable error
                    if hasattr(e, 'response') and e.response is not None:
                        if e.response.status_code not in self.config.retry.retry_on_status_codes:
                            raise  # Don't retry on non-retryable status codes
                            
                    # Calculate backoff
                    backoff = self._calculate_backoff(attempt)
                    self.logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.config.retry.max_retries + 1}), "
                        f"retrying in {backoff:.2f}s: {e}"
                    )
                    time.sleep(backoff)
                else:
                    # Max retries reached
                    self.logger.error(f"Request failed after {self.config.retry.max_retries + 1} attempts: {e}")
                    raise
                    
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
            
    def get(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for GET requests"""
        return self.request("GET", url, **kwargs)
        
    def post(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for POST requests"""
        return self.request("POST", url, use_cache=False, **kwargs)
        
    def put(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for PUT requests"""
        return self.request("PUT", url, use_cache=False, **kwargs)
        
    def delete(self, url: str, **kwargs) -> requests.Response:
        """Convenience method for DELETE requests"""
        return self.request("DELETE", url, use_cache=False, **kwargs)
        
    def set_auth(self, auth: Tuple[str, str]):
        """Set authentication for the session"""
        self.session.auth = auth
        
    def set_headers(self, headers: Dict[str, str]):
        """Update session headers"""
        self.session.headers.update(headers)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the client's performance"""
        stats = {
            "rate_limiter": {
                "current_tokens": self.rate_limiter.tokens,
                "max_tokens": self.rate_limiter.max_tokens,
            },
            "circuit_breaker": {
                "state": self.circuit_breaker.state,
                "failure_count": self.circuit_breaker.failure_count,
            }
        }
        
        if self.cache:
            stats["cache"] = {
                "entries": len(self.cache.cache_index),
                "max_size": self.cache.max_size,
            }
            
        return stats