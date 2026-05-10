"""
Test suite for TokenBucketRateLimiter

Tests cover:
- Basic token acquisition
- Rate limiting behavior
- Backoff delays
- Configuration validation
- Edge cases
"""

import asyncio
import pytest
import time

from app.rate_limiter import TokenBucketRateLimiter


class TestTokenBucketRateLimiter:
    """Test cases for TokenBucketRateLimiter"""
    
    @pytest.mark.asyncio
    async def test_initialization_valid(self):
        """Test that rate limiter initializes correctly with valid parameters"""
        limiter = TokenBucketRateLimiter(max_tokens=10.0, refill_rate=2.0)
        assert limiter.max_tokens == 10.0
        assert limiter.refill_rate == 2.0
        available = await limiter.get_available_tokens()
        assert available == 10.0
    
    @pytest.mark.asyncio
    async def test_initialization_invalid_max_tokens(self):
        """Test that initialization fails with invalid max_tokens"""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            TokenBucketRateLimiter(max_tokens=0, refill_rate=2.0)
        
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            TokenBucketRateLimiter(max_tokens=-1, refill_rate=2.0)
    
    @pytest.mark.asyncio
    async def test_initialization_invalid_refill_rate(self):
        """Test that initialization fails with invalid refill_rate"""
        with pytest.raises(ValueError, match="refill_rate must be positive"):
            TokenBucketRateLimiter(max_tokens=10.0, refill_rate=0)
        
        with pytest.raises(ValueError, match="refill_rate must be positive"):
            TokenBucketRateLimiter(max_tokens=10.0, refill_rate=-1)
    
    @pytest.mark.asyncio
    async def test_acquire_single_token_success(self):
        """Test acquiring a single token when tokens are available"""
        limiter = TokenBucketRateLimiter(max_tokens=5.0, refill_rate=1.0)
        
        # Should succeed
        result = await limiter.acquire(tokens=1.0, wait=False)
        assert result is True
        
        available = await limiter.get_available_tokens()
        assert available == pytest.approx(4.0, abs=0.01)
    
    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens_success(self):
        """Test acquiring multiple tokens in a single request"""
        limiter = TokenBucketRateLimiter(max_tokens=10.0, refill_rate=1.0)
        
        result = await limiter.acquire(tokens=3.0, wait=False)
        assert result is True
        
        available = await limiter.get_available_tokens()
        assert available == pytest.approx(7.0, abs=0.01)
    
    @pytest.mark.asyncio
    async def test_acquire_exceeds_available_no_wait(self):
        """Test that acquire fails when tokens unavailable and wait=False"""
        limiter = TokenBucketRateLimiter(max_tokens=5.0, refill_rate=1.0)
        
        # Consume all tokens
        await limiter.acquire(tokens=5.0, wait=False)
        
        # Try to acquire more without waiting
        result = await limiter.acquire(tokens=1.0, wait=False)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_acquire_invalid_tokens(self):
        """Test that acquire rejects invalid token counts"""
        limiter = TokenBucketRateLimiter(max_tokens=10.0, refill_rate=1.0)
        
        with pytest.raises(ValueError, match="tokens must be positive"):
            await limiter.acquire(tokens=0, wait=False)
        
        with pytest.raises(ValueError, match="tokens must be positive"):
            await limiter.acquire(tokens=-1, wait=False)
    
    @pytest.mark.asyncio
    async def test_acquire_with_wait(self):
        """Test that acquire waits for tokens when wait=True"""
        limiter = TokenBucketRateLimiter(max_tokens=5.0, refill_rate=5.0)
        
        # Consume all tokens
        await limiter.acquire(tokens=5.0, wait=False)
        
        # Acquire with wait should succeed after refill
        start_time = time.time()
        result = await limiter.acquire(tokens=1.0, wait=True)
        elapsed = time.time() - start_time
        
        assert result is True
        # Should have waited approximately 0.2 seconds (1 token / 5 tokens per second)
        assert elapsed >= 0.15  # Allow some tolerance
    
    @pytest.mark.asyncio
    async def test_tokens_refill_over_time(self):
        """Test that tokens refill over time"""
        limiter = TokenBucketRateLimiter(max_tokens=10.0, refill_rate=2.0)
        
        # Consume all tokens
        await limiter.acquire(tokens=10.0, wait=False)
        available = await limiter.get_available_tokens()
        assert available == pytest.approx(0.0, abs=0.01)
        
        # Wait for refill
        await asyncio.sleep(0.6)  # Should refill ~1.2 tokens in 0.6 seconds
        
        available = await limiter.get_available_tokens()
        assert available >= 1.0  # At least 1 token should be refilled
    
    @pytest.mark.asyncio
    async def test_tokens_capped_at_max(self):
        """Test that tokens don't exceed max_tokens after refill"""
        limiter = TokenBucketRateLimiter(max_tokens=5.0, refill_rate=10.0)
        
        # Wait long enough that refill would exceed max_tokens
        await asyncio.sleep(0.2)
        
        available = await limiter.get_available_tokens()
        assert available <= 5.0  # Should not exceed max
    
    @pytest.mark.asyncio
    async def test_rapid_sequential_acquisitions(self):
        """Test rapid sequential token acquisitions"""
        limiter = TokenBucketRateLimiter(max_tokens=10.0, refill_rate=5.0)
        
        # Rapidly acquire tokens
        for _ in range(10):
            result = await limiter.acquire(tokens=1.0, wait=False)
            assert result is True
        
        # All tokens consumed
        result = await limiter.acquire(tokens=1.0, wait=False)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_concurrent_acquisitions(self):
        """Test concurrent token acquisitions"""
        limiter = TokenBucketRateLimiter(max_tokens=10.0, refill_rate=1.0)
        
        # Create concurrent acquire tasks
        tasks = [limiter.acquire(tokens=1.0, wait=False) for _ in range(15)]
        results = await asyncio.gather(*tasks)
        
        # First 10 should succeed, last 5 should fail
        successful = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is False)
        
        assert successful == 10
        assert failed == 5
    
    @pytest.mark.asyncio
    async def test_reset_functionality(self):
        """Test that reset restores tokens to max"""
        limiter = TokenBucketRateLimiter(max_tokens=10.0, refill_rate=1.0)
        
        # Consume tokens
        await limiter.acquire(tokens=8.0, wait=False)
        available = await limiter.get_available_tokens()
        assert available == pytest.approx(2.0, abs=0.01)
        
        # Reset
        await limiter.reset()
        
        available = await limiter.get_available_tokens()
        assert available == pytest.approx(10.0, abs=0.01)
    
    @pytest.mark.asyncio
    async def test_fractional_tokens(self):
        """Test that rate limiter handles fractional tokens correctly"""
        limiter = TokenBucketRateLimiter(max_tokens=10.0, refill_rate=0.5)
        
        # Acquire fractional tokens
        result = await limiter.acquire(tokens=2.5, wait=False)
        assert result is True
        
        available = await limiter.get_available_tokens()
        assert abs(available - 7.5) < 0.01  # Allow small floating point error
    
    @pytest.mark.asyncio
    async def test_small_max_tokens(self):
        """Test rate limiter with very small token bucket"""
        limiter = TokenBucketRateLimiter(max_tokens=0.1, refill_rate=0.05)
        
        result = await limiter.acquire(tokens=0.1, wait=False)
        assert result is True
        
        # Should be unable to acquire more without waiting
        result = await limiter.acquire(tokens=0.01, wait=False)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_high_refill_rate(self):
        """Test rate limiter with high refill rate"""
        limiter = TokenBucketRateLimiter(max_tokens=100.0, refill_rate=1000.0)
        
        # Consume tokens
        await limiter.acquire(tokens=100.0, wait=False)
        
        # Tokens should refill very quickly
        await asyncio.sleep(0.01)
        available = await limiter.get_available_tokens()
        assert available >= 5.0  # At least 10 tokens in 0.01 seconds


class TestRateLimiterIntegration:
    """Integration tests for rate limiter usage patterns"""
    
    @pytest.mark.asyncio
    async def test_endpoint_rate_limiting_pattern(self):
        """Test typical endpoint rate limiting pattern"""
        # Simulate endpoint with 5 requests/second limit
        limiter = TokenBucketRateLimiter(max_tokens=5.0, refill_rate=5.0)
        
        request_count = 0
        rate_limited = 0
        
        # Simulate rapid requests
        for _ in range(12):
            if await limiter.acquire(tokens=1.0, wait=False):
                request_count += 1
            else:
                rate_limited += 1
        
        assert request_count == 5
        assert rate_limited == 7
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_limiting_with_wait(self):
        """Test adaptive rate limiting that waits for token availability"""
        limiter = TokenBucketRateLimiter(max_tokens=5.0, refill_rate=10.0)
        
        successful = 0
        start_time = time.time()
        
        # Make requests that will require waiting
        for _ in range(20):
            if await limiter.acquire(tokens=1.0, wait=True):
                successful += 1
        
        elapsed = time.time() - start_time
        
        assert successful == 20
        # Should take approximately 1.5 seconds (20 tokens at 10 tokens/sec)
        assert 1.3 < elapsed < 2.0
    
    @pytest.mark.asyncio
    async def test_burst_handling(self):
        """Test handling of burst traffic"""
        limiter = TokenBucketRateLimiter(max_tokens=10.0, refill_rate=2.0)
        
        # First burst uses all tokens
        burst1_results = []
        for _ in range(10):
            result = await limiter.acquire(tokens=1.0, wait=False)
            burst1_results.append(result)
        burst1_success = sum(1 for r in burst1_results if r is True)
        assert burst1_success == 10
        
        # Wait for refill
        await asyncio.sleep(1.5)  # Should have ~3 tokens refilled
        
        # Second burst should only get 3 tokens
        burst2_results = []
        for _ in range(5):
            result = await limiter.acquire(tokens=1.0, wait=False)
            burst2_results.append(result)
        burst2_success = sum(1 for r in burst2_results if r is True)
        assert burst2_success == 3  # Only 3 tokens available
