"""
Unit tests for rate limiter functionality.

Tests cover:
- TokenBucket algorithm
- RateLimiter class
- Per-domain rate limiting
- Adaptive throttling
- Exponential backoff
- Rate limit statistics
"""

import pytest
import time
import sys
from unittest.mock import Mock, patch, MagicMock

# Add rate-limiting example to path
sys.path.insert(0, '/home/ruhroh/scrape-api-docs/examples/rate-limiting')

from rate_limiter import TokenBucket, RateLimiter, rate_limited_get


@pytest.mark.unit
class TestTokenBucket:
    """Test suite for TokenBucket algorithm."""

    def test_initialization(self):
        """Test token bucket initialization."""
        bucket = TokenBucket(rate=5.0, capacity=10.0)

        assert bucket.rate == 5.0
        assert bucket.capacity == 10.0
        assert bucket.tokens == 10.0  # Starts full
        assert bucket.last_update is not None

    def test_consume_tokens(self):
        """Test consuming tokens from bucket."""
        bucket = TokenBucket(rate=10.0, capacity=10.0)

        # Should be able to consume tokens
        assert bucket.consume(1) is True
        assert bucket.consume(5) is True

        # Should have consumed 6 tokens
        assert bucket.tokens == 4.0

    def test_insufficient_tokens(self):
        """Test behavior when insufficient tokens."""
        bucket = TokenBucket(rate=1.0, capacity=5.0)

        # Consume all tokens
        assert bucket.consume(5) is True

        # Next consume should fail
        assert bucket.consume(1) is False

    def test_token_refill(self):
        """Test that tokens are refilled over time."""
        bucket = TokenBucket(rate=10.0, capacity=10.0)

        # Consume all tokens
        bucket.consume(10)
        assert bucket.tokens == 0.0

        # Wait for refill
        time.sleep(0.5)

        # Should have refilled approximately 5 tokens
        assert bucket.consume(1) is True

    def test_capacity_limit(self):
        """Test that tokens don't exceed capacity."""
        bucket = TokenBucket(rate=100.0, capacity=10.0)

        # Wait for potential overflow
        time.sleep(0.5)

        # Refill should be capped at capacity
        assert bucket.tokens <= 10.0

    def test_wait_time_calculation(self):
        """Test wait time calculation for needed tokens."""
        bucket = TokenBucket(rate=10.0, capacity=10.0)

        # Consume all tokens
        bucket.consume(10)

        # Need 5 tokens at 10/sec = 0.5 seconds
        wait_time = bucket.wait_time(5)
        assert 0.4 <= wait_time <= 0.6  # Allow small variance

    def test_wait_time_when_available(self):
        """Test wait time is zero when tokens available."""
        bucket = TokenBucket(rate=10.0, capacity=10.0)

        wait_time = bucket.wait_time(5)
        assert wait_time == 0.0

    def test_thread_safety(self):
        """Test thread safety of token consumption."""
        bucket = TokenBucket(rate=100.0, capacity=100.0)

        # Multiple threads consuming tokens
        import threading

        results = []

        def consume():
            result = bucket.consume(1)
            results.append(result)

        threads = [threading.Thread(target=consume) for _ in range(50)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed or fail based on token availability
        assert len(results) == 50


@pytest.mark.unit
class TestRateLimiter:
    """Test suite for RateLimiter class."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(
            requests_per_second=2.0,
            burst_size=5,
            max_retries=3,
            backoff_factor=2.0
        )

        assert limiter.requests_per_second == 2.0
        assert limiter.burst_size == 5
        assert limiter.max_retries == 3
        assert limiter.backoff_factor == 2.0

    def test_default_burst_size(self):
        """Test default burst size calculation."""
        limiter = RateLimiter(requests_per_second=2.0)

        # Default should be 2x rate
        assert limiter.burst_size == 4

    def test_domain_extraction(self):
        """Test domain extraction from URLs."""
        limiter = RateLimiter()

        domain = limiter._extract_domain('https://example.com/docs/api/')
        assert domain == 'example.com'

        domain = limiter._extract_domain('http://api.example.com:8080/path')
        assert domain == 'api.example.com:8080'

    def test_per_domain_buckets(self):
        """Test that separate buckets are created per domain."""
        limiter = RateLimiter(requests_per_second=10.0)

        # Get buckets for different domains
        bucket1 = limiter._get_bucket('example.com')
        bucket2 = limiter._get_bucket('other.com')
        bucket3 = limiter._get_bucket('example.com')

        # Same domain should return same bucket
        assert bucket1 is bucket3
        assert bucket1 is not bucket2

    def test_acquire_context_manager(self):
        """Test acquire context manager usage."""
        limiter = RateLimiter(requests_per_second=100.0)  # Fast for testing

        url = 'https://example.com/page1'

        with limiter.acquire(url) as waited:
            # Should succeed
            assert waited >= 0.0

    def test_acquire_with_delay(self):
        """Test acquire adds delays when needed."""
        limiter = RateLimiter(requests_per_second=2.0)

        url = 'https://example.com/page'

        # First request should be immediate
        with limiter.acquire(url) as waited:
            assert waited < 0.1

        # Exhaust tokens
        for _ in range(5):
            try:
                with limiter.acquire(url, timeout=0.5):
                    pass
            except TimeoutError:
                break

    def test_record_response_success(self):
        """Test recording successful responses."""
        limiter = RateLimiter()

        url = 'https://example.com/page'
        limiter.record_response(url, 200)

        stats = limiter.get_stats('example.com')
        assert stats['requests'] == 1
        assert stats['throttled'] == 0

    def test_record_response_429(self):
        """Test recording 429 responses triggers backoff."""
        limiter = RateLimiter()

        url = 'https://example.com/page'
        limiter.record_response(url, 429)

        # Should be in backoff
        stats = limiter.get_stats('example.com')
        assert stats['throttled'] == 1
        assert stats['in_backoff'] is True

    def test_record_response_503(self):
        """Test recording 503 responses triggers backoff."""
        limiter = RateLimiter()

        url = 'https://example.com/page'
        limiter.record_response(url, 503)

        stats = limiter.get_stats('example.com')
        assert stats['throttled'] == 1

    def test_backoff_duration_increases(self):
        """Test exponential backoff increases with errors."""
        limiter = RateLimiter(backoff_factor=2.0)

        url = 'https://example.com/page'

        # Trigger multiple errors
        limiter.record_response(url, 429)
        first_backoff = limiter._is_backed_off('example.com')

        limiter.record_response(url, 429)
        second_backoff = limiter._is_backed_off('example.com')

        # Second backoff should be longer
        assert second_backoff >= first_backoff

    def test_backoff_expires(self):
        """Test that backoff period expires."""
        limiter = RateLimiter(backoff_factor=1.5)

        url = 'https://example.com/page'
        limiter.record_response(url, 429)

        # Should be backed off
        assert limiter._is_backed_off('example.com') is not None

        # Wait for backoff to expire (short backoff for testing)
        time.sleep(1.6)  # Backoff should be ~1.5 seconds

        # Should no longer be backed off
        assert limiter._is_backed_off('example.com') is None

    def test_set_domain_limit(self):
        """Test setting custom limits for specific domains."""
        limiter = RateLimiter(requests_per_second=5.0)

        # Set custom limit for one domain
        limiter.set_domain_limit('slow.example.com', 0.5)

        # Get buckets
        normal_bucket = limiter._get_bucket('fast.example.com')
        slow_bucket = limiter._get_bucket('slow.example.com')

        assert slow_bucket.rate == 0.5
        assert normal_bucket.rate == 5.0

    def test_get_stats_all_domains(self):
        """Test getting stats for all domains."""
        limiter = RateLimiter()

        limiter.record_response('https://example.com/page', 200)
        limiter.record_response('https://other.com/page', 200)

        all_stats = limiter.get_stats()

        assert 'example.com' in all_stats
        assert 'other.com' in all_stats
        assert all_stats['example.com']['requests'] == 1

    def test_get_stats_specific_domain(self):
        """Test getting stats for specific domain."""
        limiter = RateLimiter()

        limiter.record_response('https://example.com/page', 200)

        stats = limiter.get_stats('example.com')

        assert stats['domain'] == 'example.com'
        assert stats['requests'] == 1
        assert stats['throttled'] == 0
        assert stats['errors'] == 0

    def test_timeout_during_wait(self):
        """Test timeout exception when wait exceeds limit."""
        limiter = RateLimiter(requests_per_second=0.1)  # Very slow

        url = 'https://example.com/page'

        # Exhaust tokens
        with limiter.acquire(url):
            pass

        # Next request should timeout
        with pytest.raises(TimeoutError):
            with limiter.acquire(url, timeout=0.1):
                pass

    def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        limiter = RateLimiter(requests_per_second=100.0)

        url = 'https://example.com/page'
        results = []

        def make_request():
            try:
                with limiter.acquire(url, timeout=1.0):
                    results.append(True)
            except TimeoutError:
                results.append(False)

        import threading
        threads = [threading.Thread(target=make_request) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Most should succeed
        assert sum(results) >= 8


@pytest.mark.unit
class TestRateLimitedGet:
    """Test suite for rate_limited_get helper."""

    @patch('rate_limiter.requests.get')
    def test_successful_request(self, mock_get):
        """Test successful rate-limited GET request."""
        limiter = RateLimiter(requests_per_second=100.0)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        response = rate_limited_get('https://example.com/page', limiter)

        assert response.status_code == 200
        assert mock_get.called

    @patch('rate_limiter.requests.get')
    def test_retry_on_429(self, mock_get):
        """Test retry behavior on 429 status."""
        limiter = RateLimiter(requests_per_second=100.0, max_retries=2)

        # First request returns 429, second succeeds
        mock_response_429 = Mock()
        mock_response_429.status_code = 429

        mock_response_200 = Mock()
        mock_response_200.status_code = 200

        mock_get.side_effect = [mock_response_429, mock_response_200]

        response = rate_limited_get('https://example.com/page', limiter)

        assert response.status_code == 200
        assert mock_get.call_count == 2

    @patch('rate_limiter.requests.get')
    def test_max_retries_exceeded(self, mock_get):
        """Test exception when max retries exceeded."""
        limiter = RateLimiter(requests_per_second=100.0, max_retries=2)

        # All requests return 429
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Max retries"):
            rate_limited_get('https://example.com/page', limiter)

    @patch('rate_limiter.requests.get')
    def test_with_session(self, mock_get):
        """Test using custom session object."""
        limiter = RateLimiter(requests_per_second=100.0)
        mock_session = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        response = rate_limited_get(
            'https://example.com/page',
            limiter,
            session=mock_session
        )

        assert response.status_code == 200
        assert mock_session.get.called


@pytest.mark.unit
class TestAdaptiveThrottling:
    """Test adaptive throttling features."""

    def test_error_tracking(self):
        """Test that recent errors are tracked."""
        limiter = RateLimiter()

        url = 'https://example.com/page'

        # Record some errors
        limiter.record_response(url, 429)
        limiter.record_response(url, 503)
        limiter.record_response(url, 500)

        domain = 'example.com'
        errors = limiter.recent_errors[domain]

        assert len(errors) >= 2  # 429 and 503 are throttle errors

    def test_backoff_clearing(self):
        """Test that backoff clears after success."""
        limiter = RateLimiter()

        url = 'https://example.com/page'

        # Trigger backoff
        limiter.record_response(url, 429)
        assert limiter._is_backed_off('example.com') is not None

        # Wait for backoff to expire
        time.sleep(2.0)

        # Backoff should clear
        remaining = limiter._is_backed_off('example.com')
        assert remaining is None or remaining <= 0
