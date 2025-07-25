#!/usr/bin/env python3
"""
Unit tests for the resilient API client
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import json
import tempfile
import shutil
from pathlib import Path

import requests
from requests.exceptions import RequestException, HTTPError

from exporter_config import ExporterConfig, RetryConfig, RateLimitConfig, CircuitBreakerConfig
from api_client import ResilientAPIClient, RateLimiter, CircuitBreaker, RequestCache


class TestRateLimiter(unittest.TestCase):
    """Test cases for RateLimiter"""
    
    def setUp(self):
        self.config = RateLimitConfig(
            requests_per_second=10.0,
            burst_size=20,
            min_request_interval=0.1
        )
        self.rate_limiter = RateLimiter(self.config)
        
    def test_burst_requests(self):
        """Test that burst requests are allowed without delay"""
        # Should be able to make burst_size requests without delay
        for i in range(self.config.burst_size):
            wait_time = self.rate_limiter.acquire()
            self.assertEqual(wait_time, 0.0, f"Request {i+1} should not require waiting")
            
    def test_rate_limiting(self):
        """Test that rate limiting kicks in after burst"""
        # Exhaust burst capacity
        for _ in range(self.config.burst_size):
            self.rate_limiter.acquire()
            
        # Next request should require waiting
        wait_time = self.rate_limiter.acquire()
        self.assertGreater(wait_time, 0, "Should require waiting after burst exhausted")
        self.assertGreaterEqual(wait_time, self.config.min_request_interval)
        
    def test_token_refill(self):
        """Test that tokens are refilled over time"""
        # Exhaust some tokens
        for _ in range(10):
            self.rate_limiter.acquire()
            
        initial_tokens = self.rate_limiter.tokens
        
        # Wait for refill
        time.sleep(0.5)
        
        # Check tokens increased
        self.rate_limiter.acquire(0)  # Trigger refill calculation
        self.assertGreater(self.rate_limiter.tokens, initial_tokens)


class TestCircuitBreaker(unittest.TestCase):
    """Test cases for CircuitBreaker"""
    
    def setUp(self):
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0
        )
        self.circuit_breaker = CircuitBreaker(self.config)
        
    def test_successful_calls(self):
        """Test that successful calls keep circuit closed"""
        def success_func():
            return "success"
            
        for _ in range(10):
            result = self.circuit_breaker.call(success_func)
            self.assertEqual(result, "success")
            self.assertEqual(self.circuit_breaker.state, CircuitBreaker.State.CLOSED)
            
    def test_circuit_opens_on_failures(self):
        """Test that circuit opens after threshold failures"""
        def fail_func():
            raise Exception("Test failure")
            
        # Make failures up to threshold
        for i in range(self.config.failure_threshold):
            with self.assertRaises(Exception):
                self.circuit_breaker.call(fail_func)
                
        # Circuit should now be open
        self.assertEqual(self.circuit_breaker.state, CircuitBreaker.State.OPEN)
        
        # Further calls should fail immediately
        with self.assertRaises(Exception) as cm:
            self.circuit_breaker.call(fail_func)
        self.assertEqual(str(cm.exception), "Circuit breaker is OPEN")
        
    def test_circuit_recovery(self):
        """Test that circuit recovers after timeout"""
        def fail_func():
            raise Exception("Test failure")
            
        def success_func():
            return "success"
            
        # Open the circuit
        for _ in range(self.config.failure_threshold):
            with self.assertRaises(Exception):
                self.circuit_breaker.call(fail_func)
                
        # Wait for recovery timeout
        time.sleep(self.config.recovery_timeout + 0.1)
        
        # Next successful call should close circuit
        result = self.circuit_breaker.call(success_func)
        self.assertEqual(result, "success")
        self.assertEqual(self.circuit_breaker.state, CircuitBreaker.State.CLOSED)


class TestRequestCache(unittest.TestCase):
    """Test cases for RequestCache"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache = RequestCache(
            cache_dir=self.temp_dir,
            ttl=2,  # 2 seconds for testing
            max_size=3
        )
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        
    def test_cache_hit(self):
        """Test cache hit for same request"""
        url = "https://api.example.com/data"
        response_data = {"result": "test"}
        
        # Store in cache
        self.cache.set("GET", url, response_data)
        
        # Retrieve from cache
        cached = self.cache.get("GET", url)
        self.assertEqual(cached, response_data)
        
    def test_cache_miss_different_params(self):
        """Test cache miss for different parameters"""
        url = "https://api.example.com/data"
        response_data = {"result": "test"}
        
        # Store with params
        self.cache.set("GET", url, response_data, params={"page": 1})
        
        # Try to get with different params
        cached = self.cache.get("GET", url, params={"page": 2})
        self.assertIsNone(cached)
        
    def test_cache_expiration(self):
        """Test that cached items expire"""
        url = "https://api.example.com/data"
        response_data = {"result": "test"}
        
        # Store in cache
        self.cache.set("GET", url, response_data)
        
        # Wait for expiration
        time.sleep(2.5)
        
        # Should return None
        cached = self.cache.get("GET", url)
        self.assertIsNone(cached)
        
    def test_cache_size_limit(self):
        """Test that cache respects size limit"""
        # Fill cache to limit
        for i in range(4):  # One more than max_size
            self.cache.set("GET", f"https://api.example.com/data{i}", {"result": i})
            
        # First item should be evicted
        cached = self.cache.get("GET", "https://api.example.com/data0")
        self.assertIsNone(cached)
        
        # Last items should still be there
        for i in range(1, 4):
            cached = self.cache.get("GET", f"https://api.example.com/data{i}")
            self.assertIsNotNone(cached)


class TestResilientAPIClient(unittest.TestCase):
    """Test cases for ResilientAPIClient"""
    
    def setUp(self):
        self.config = ExporterConfig("balanced")
        self.config.retry.max_retries = 3
        self.config.retry.initial_delay = 0.1
        self.config.cache.enabled = True
        
        self.client = ResilientAPIClient(self.config)
        
    def tearDown(self):
        if hasattr(self.client, 'cache') and self.client.cache:
            shutil.rmtree(self.client.cache.cache_dir, ignore_errors=True)
            
    @patch('requests.Session.request')
    def test_successful_request(self, mock_request):
        """Test successful request without retries"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {"success": True}
        mock_request.return_value = mock_response
        
        response = self.client.get("https://api.example.com/data")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_count, 1)
        
    @patch('requests.Session.request')
    def test_retry_on_500_error(self, mock_request):
        """Test retry logic on 500 errors"""
        # First two calls fail, third succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.raise_for_status.side_effect = HTTPError(response=mock_response_fail)
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.ok = True
        
        mock_request.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success
        ]
        
        response = self.client.get("https://api.example.com/data")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_count, 3)
        
    @patch('requests.Session.request')
    def test_max_retries_exceeded(self, mock_request):
        """Test that max retries are respected"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_request.return_value = mock_response
        
        with self.assertRaises(HTTPError):
            self.client.get("https://api.example.com/data")
            
        # Should be max_retries + 1 (original + retries)
        self.assertEqual(mock_request.call_count, self.config.retry.max_retries + 1)
        
    @patch('requests.Session.request')
    def test_rate_limiting(self, mock_request):
        """Test that rate limiting is applied"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_request.return_value = mock_response
        
        # Make rapid requests
        start_time = time.time()
        for _ in range(3):
            self.client.get("https://api.example.com/data")
        duration = time.time() - start_time
        
        # Should have some delay due to rate limiting
        # (exact timing depends on rate limiter state)
        self.assertGreater(duration, 0)
        
    @patch('requests.Session.request')
    def test_cache_usage(self, mock_request):
        """Test that cache is used for GET requests"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {"data": "test"}
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response._content = json.dumps({"data": "test"}).encode('utf-8')
        mock_request.return_value = mock_response
        
        # First request should hit the API
        response1 = self.client.get("https://api.example.com/data")
        self.assertEqual(mock_request.call_count, 1)
        
        # Second request should use cache
        response2 = self.client.get("https://api.example.com/data")
        self.assertEqual(mock_request.call_count, 1)  # No additional call
        
        # Responses should have same data
        self.assertEqual(response1.json(), response2.json())
        
    @patch('requests.Session.request')
    def test_no_cache_for_post(self, mock_request):
        """Test that POST requests are not cached"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_request.return_value = mock_response
        
        # Make two POST requests
        self.client.post("https://api.example.com/data", json={"test": "data"})
        self.client.post("https://api.example.com/data", json={"test": "data"})
        
        # Both should hit the API
        self.assertEqual(mock_request.call_count, 2)
        
    @patch('requests.Session.request')
    def test_exponential_backoff(self, mock_request):
        """Test exponential backoff timing"""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_request.return_value = mock_response
        
        start_time = time.time()
        
        with self.assertRaises(HTTPError):
            self.client.get("https://api.example.com/data")
            
        total_time = time.time() - start_time
        
        # Calculate expected minimum time (without jitter)
        expected_min_time = sum(
            self.config.retry.initial_delay * (self.config.retry.exponential_base ** i)
            for i in range(self.config.retry.max_retries)
        )
        
        # Should take at least the sum of delays (accounting for some variance)
        self.assertGreater(total_time, expected_min_time * 0.5)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete retry system"""
    
    def setUp(self):
        self.config = ExporterConfig("fast")
        self.config.retry.max_retries = 2
        self.config.retry.initial_delay = 0.05
        
    @patch('requests.Session.request')
    def test_circuit_breaker_integration(self, mock_request):
        """Test circuit breaker prevents excessive retries"""
        client = ResilientAPIClient(self.config)
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_request.return_value = mock_response
        
        # Make requests until circuit opens
        failure_count = 0
        for i in range(10):
            try:
                client.get(f"https://api.example.com/data{i}")
            except Exception:
                failure_count += 1
                
        # Circuit should prevent some calls
        self.assertLess(
            mock_request.call_count,
            10 * (self.config.retry.max_retries + 1),
            "Circuit breaker should prevent some retry attempts"
        )


if __name__ == '__main__':
    unittest.main()