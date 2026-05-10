"""
Tests for Chaos Engine Fault Injection

Comprehensive test suite covering all chaos engine functionality.
"""

import pytest
import asyncio

from app.chaos_engine import (
    FaultType,
    EndpointFilter,
    ChaosConfig,
    ChaosEngine,
    ChaosInjectionError,
)


class TestChaosConfig:
    """Tests for ChaosConfig dataclass."""

    def test_valid_config(self):
        """Test creating a valid ChaosConfig."""
        config = ChaosConfig(
            fault_type=FaultType.NETWORK_TIMEOUT,
            probability=0.5,
            affected_endpoints={EndpointFilter.PROVISION_LINK},
        )
        assert config.fault_type == FaultType.NETWORK_TIMEOUT
        assert config.probability == 0.5
        assert config.latency_ms == 0

    def test_config_with_all_parameters(self):
        """Test ChaosConfig with all optional parameters."""
        config = ChaosConfig(
            fault_type=FaultType.LATENCY,
            probability=0.3,
            affected_endpoints={EndpointFilter.FETCH_KMS_STATUS, EndpointFilter.POLL_KMS},
            duration_seconds=60,
            latency_ms=500,
            error_details="Custom error message",
        )
        assert config.latency_ms == 500
        assert config.duration_seconds == 60
        assert config.error_details == "Custom error message"
        assert len(config.affected_endpoints) == 2

    def test_invalid_probability_too_high(self):
        """Test ChaosConfig rejects probability > 1.0."""
        with pytest.raises(ValueError, match="Probability must be between 0.0 and 1.0"):
            ChaosConfig(
                fault_type=FaultType.HTTP_500,
                probability=1.5,
            )

    def test_invalid_probability_negative(self):
        """Test ChaosConfig rejects negative probability."""
        with pytest.raises(ValueError, match="Probability must be between 0.0 and 1.0"):
            ChaosConfig(
                fault_type=FaultType.HTTP_500,
                probability=-0.1,
            )

    def test_invalid_duration(self):
        """Test ChaosConfig rejects invalid duration."""
        with pytest.raises(ValueError, match="Duration must be positive"):
            ChaosConfig(
                fault_type=FaultType.HTTP_500,
                probability=0.5,
                duration_seconds=-1,
            )

    def test_invalid_latency(self):
        """Test ChaosConfig rejects negative latency."""
        with pytest.raises(ValueError, match="Latency must be non-negative"):
            ChaosConfig(
                fault_type=FaultType.LATENCY,
                probability=0.5,
                latency_ms=-100,
            )

    def test_edge_case_probability_zero(self):
        """Test ChaosConfig allows probability 0.0."""
        config = ChaosConfig(
            fault_type=FaultType.HTTP_500,
            probability=0.0,
        )
        assert config.probability == 0.0

    def test_edge_case_probability_one(self):
        """Test ChaosConfig allows probability 1.0."""
        config = ChaosConfig(
            fault_type=FaultType.HTTP_500,
            probability=1.0,
        )
        assert config.probability == 1.0


class TestChaosEngine:
    """Tests for ChaosEngine functionality."""

    def test_engine_initialization(self):
        """Test ChaosEngine initializes correctly."""
        engine = ChaosEngine(enabled=True)
        assert engine.is_enabled()

    def test_engine_disabled_initialization(self):
        """Test ChaosEngine can be initialized disabled."""
        engine = ChaosEngine(enabled=False)
        assert not engine.is_enabled()

    def test_enable_disable_engine(self):
        """Test enabling and disabling the engine."""
        engine = ChaosEngine(enabled=False)
        assert not engine.is_enabled()
        
        engine.set_enabled(True)
        assert engine.is_enabled()
        
        engine.set_enabled(False)
        assert not engine.is_enabled()

    @pytest.mark.asyncio
    async def test_inject_fault(self):
        """Test injecting a single fault."""
        engine = ChaosEngine(enabled=True)
        config = ChaosConfig(
            fault_type=FaultType.NETWORK_TIMEOUT,
            probability=1.0,
        )
        
        fault_id = await engine.inject_fault(config)
        assert fault_id
        assert len(fault_id) > 0

    @pytest.mark.asyncio
    async def test_inject_multiple_faults(self):
        """Test injecting multiple faults."""
        engine = ChaosEngine(enabled=True)
        fault_ids = []
        
        for i in range(3):
            config = ChaosConfig(
                fault_type=FaultType.HTTP_500,
                probability=0.5,
            )
            fault_id = await engine.inject_fault(config)
            fault_ids.append(fault_id)
        
        # All fault IDs should be unique
        assert len(set(fault_ids)) == 3
        
        # Get active faults
        faults = await engine.get_active_faults()
        assert len(faults) == 3

    @pytest.mark.asyncio
    async def test_remove_fault(self):
        """Test removing an injected fault."""
        engine = ChaosEngine(enabled=True)
        config = ChaosConfig(
            fault_type=FaultType.NETWORK_TIMEOUT,
            probability=1.0,
        )
        
        fault_id = await engine.inject_fault(config)
        assert len(await engine.get_active_faults()) == 1
        
        # Remove the fault
        removed = await engine.remove_fault(fault_id)
        assert removed
        assert len(await engine.get_active_faults()) == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_fault(self):
        """Test removing a fault that doesn't exist."""
        engine = ChaosEngine(enabled=True)
        removed = await engine.remove_fault("nonexistent-fault-id")
        assert not removed

    @pytest.mark.asyncio
    async def test_clear_all_faults(self):
        """Test clearing all faults."""
        engine = ChaosEngine(enabled=True)
        
        # Inject 5 faults
        for i in range(5):
            config = ChaosConfig(
                fault_type=FaultType.HTTP_429,
                probability=0.5,
            )
            await engine.inject_fault(config)
        
        assert len(await engine.get_active_faults()) == 5
        
        # Clear all
        cleared = await engine.clear_all_faults()
        assert cleared == 5
        assert len(await engine.get_active_faults()) == 0

    @pytest.mark.asyncio
    async def test_no_fault_when_disabled(self):
        """Test that disabled engine doesn't inject faults."""
        engine = ChaosEngine(enabled=False)
        config = ChaosConfig(
            fault_type=FaultType.NETWORK_TIMEOUT,
            probability=1.0,
        )
        
        fault_id = await engine.inject_fault(config)
        assert fault_id == ""

    @pytest.mark.asyncio
    async def test_should_inject_fault_probability_one(self):
        """Test fault injection with probability 1.0."""
        engine = ChaosEngine(enabled=True)
        config = ChaosConfig(
            fault_type=FaultType.NETWORK_TIMEOUT,
            probability=1.0,
            affected_endpoints={EndpointFilter.PROVISION_LINK},
        )
        
        await engine.inject_fault(config)
        
        # With probability 1.0, fault should always be triggered
        for _ in range(10):
            fault = await engine.should_inject_fault(EndpointFilter.PROVISION_LINK)
            assert fault == FaultType.NETWORK_TIMEOUT

    @pytest.mark.asyncio
    async def test_should_inject_fault_probability_zero(self):
        """Test fault injection with probability 0.0."""
        engine = ChaosEngine(enabled=True)
        config = ChaosConfig(
            fault_type=FaultType.HTTP_500,
            probability=0.0,
            affected_endpoints={EndpointFilter.FETCH_KMS_STATUS},
        )
        
        await engine.inject_fault(config)
        
        # With probability 0.0, fault should never be triggered
        for _ in range(10):
            fault = await engine.should_inject_fault(EndpointFilter.FETCH_KMS_STATUS)
            assert fault is None

    @pytest.mark.asyncio
    async def test_should_inject_fault_endpoint_filtering(self):
        """Test fault injection with endpoint filtering."""
        engine = ChaosEngine(enabled=True)
        
        # Inject fault for PROVISION_LINK only
        config = ChaosConfig(
            fault_type=FaultType.NETWORK_TIMEOUT,
            probability=1.0,
            affected_endpoints={EndpointFilter.PROVISION_LINK},
        )
        await engine.inject_fault(config)
        
        # Should be triggered for PROVISION_LINK
        fault = await engine.should_inject_fault(EndpointFilter.PROVISION_LINK)
        assert fault == FaultType.NETWORK_TIMEOUT
        
        # Should NOT be triggered for other endpoints
        fault = await engine.should_inject_fault(EndpointFilter.FETCH_KMS_STATUS)
        assert fault is None

    @pytest.mark.asyncio
    async def test_should_inject_fault_all_endpoints(self):
        """Test fault injection affecting all endpoints."""
        engine = ChaosEngine(enabled=True)
        
        # Inject fault for ALL endpoints
        config = ChaosConfig(
            fault_type=FaultType.HTTP_500,
            probability=1.0,
            affected_endpoints={EndpointFilter.ALL},
        )
        await engine.inject_fault(config)
        
        # Should be triggered for all endpoints
        for endpoint in [EndpointFilter.PROVISION_LINK, EndpointFilter.FETCH_KMS_STATUS, EndpointFilter.POLL_KMS]:
            fault = await engine.should_inject_fault(endpoint)
            assert fault == FaultType.HTTP_500

    @pytest.mark.asyncio
    async def test_fault_expiration(self):
        """Test that faults expire after configured duration."""
        engine = ChaosEngine(enabled=True)
        
        # Inject fault with 0.5 second duration
        config = ChaosConfig(
            fault_type=FaultType.TRANSIENT_ERROR,
            probability=1.0,
            duration_seconds=0.5,
            affected_endpoints={EndpointFilter.PROVISION_LINK},
        )
        await engine.inject_fault(config)
        
        # Fault should be active immediately
        assert len(await engine.get_active_faults()) == 1
        
        # Fault should be triggered
        fault = await engine.should_inject_fault(EndpointFilter.PROVISION_LINK)
        assert fault == FaultType.TRANSIENT_ERROR
        
        # Wait for expiration
        await asyncio.sleep(0.6)
        
        # Fault should no longer be active
        assert len(await engine.get_active_faults()) == 0

    @pytest.mark.asyncio
    async def test_get_active_faults(self):
        """Test getting list of active faults."""
        engine = ChaosEngine(enabled=True)
        
        config1 = ChaosConfig(
            fault_type=FaultType.NETWORK_TIMEOUT,
            probability=0.5,
            affected_endpoints={EndpointFilter.PROVISION_LINK},
        )
        config2 = ChaosConfig(
            fault_type=FaultType.HTTP_500,
            probability=0.8,
            affected_endpoints={EndpointFilter.FETCH_KMS_STATUS},
        )
        
        fault_id1 = await engine.inject_fault(config1)
        fault_id2 = await engine.inject_fault(config2)
        
        faults = await engine.get_active_faults()
        assert len(faults) == 2
        
        fault_ids = [f["fault_id"] for f in faults]
        assert fault_id1 in fault_ids
        assert fault_id2 in fault_ids

    @pytest.mark.asyncio
    async def test_get_fault_details(self):
        """Test getting details about a specific fault."""
        engine = ChaosEngine(enabled=True)
        
        config = ChaosConfig(
            fault_type=FaultType.LATENCY,
            probability=0.6,
            latency_ms=500,
            error_details="Test latency fault",
            affected_endpoints={EndpointFilter.POLL_KMS},
        )
        
        fault_id = await engine.inject_fault(config)
        
        details = await engine.get_fault_details(fault_id)
        assert details is not None
        assert details["fault_id"] == fault_id
        assert details["fault_type"] == FaultType.LATENCY.value
        assert details["probability"] == 0.6
        assert details["latency_ms"] == 500
        assert details["error_details"] == "Test latency fault"

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test getting chaos engine statistics."""
        engine = ChaosEngine(enabled=True)
        
        # Inject a fault with probability 1.0 to guarantee triggering
        config = ChaosConfig(
            fault_type=FaultType.HTTP_500,
            probability=1.0,
            affected_endpoints={EndpointFilter.PROVISION_LINK},
        )
        await engine.inject_fault(config)
        
        # Trigger the fault a few times
        for _ in range(3):
            await engine.should_inject_fault(EndpointFilter.PROVISION_LINK)
        
        stats = await engine.get_statistics()
        assert stats["enabled"]
        assert stats["active_faults"] == 1
        assert stats["total_injections"] == 3
        assert FaultType.HTTP_500.value in stats["faults_by_type"]

    @pytest.mark.asyncio
    async def test_injection_counter_increments(self):
        """Test that injection counter increments."""
        engine = ChaosEngine(enabled=True)
        
        config = ChaosConfig(
            fault_type=FaultType.PARTIAL_RESPONSE,
            probability=1.0,
        )
        fault_id = await engine.inject_fault(config)
        
        # Trigger fault multiple times
        for i in range(5):
            await engine.should_inject_fault(EndpointFilter.ALL)
            details = await engine.get_fault_details(fault_id)
            assert details["injection_count"] == i + 1
            assert details["trigger_count"] == i + 1

    @pytest.mark.asyncio
    async def test_multiple_faults_different_types(self):
        """Test handling multiple faults of different types."""
        engine = ChaosEngine(enabled=True)
        
        fault_types = [
            FaultType.NETWORK_TIMEOUT,
            FaultType.HTTP_500,
            FaultType.MALFORMED_RESPONSE,
        ]
        
        for fault_type in fault_types:
            config = ChaosConfig(
                fault_type=fault_type,
                probability=1.0,
                affected_endpoints={EndpointFilter.ALL},
            )
            await engine.inject_fault(config)
        
        faults = await engine.get_active_faults()
        assert len(faults) == 3
        
        fault_types_found = {f["fault_type"] for f in faults}
        expected_types = {ft.value for ft in fault_types}
        assert fault_types_found == expected_types

    @pytest.mark.asyncio
    async def test_chaos_injection_error(self):
        """Test ChaosInjectionError exception."""
        error = ChaosInjectionError(
            FaultType.NETWORK_TIMEOUT,
            "Network connection failed",
        )
        
        assert error.fault_type == FaultType.NETWORK_TIMEOUT
        assert error.details == "Network connection failed"
        assert "Chaos injection triggered" in str(error)

    @pytest.mark.asyncio
    async def test_concurrent_fault_injection(self):
        """Test concurrent fault injection operations."""
        engine = ChaosEngine(enabled=True)
        
        async def inject_and_check():
            config = ChaosConfig(
                fault_type=FaultType.HTTP_429,
                probability=0.8,
            )
            fault_id = await engine.inject_fault(config)
            await asyncio.sleep(0.01)
            fault = await engine.should_inject_fault(EndpointFilter.ALL)
            return fault_id, fault
        
        # Run 10 concurrent operations
        results = await asyncio.gather(*[inject_and_check() for _ in range(10)])
        
        fault_ids = [r[0] for r in results]
        # All fault IDs should be unique
        assert len(set(fault_ids)) == 10
        
        # Should have 10 active faults
        faults = await engine.get_active_faults()
        assert len(faults) == 10
