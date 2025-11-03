"""Tests for secrets management."""

import os
import pytest
from internal_base import (
    EnvironmentSecretsProvider,
    CachedSecretsProvider,
    ChainedSecretsProvider,
    SecretsManager,
    SecretValue,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_environment_secrets_provider():
    """Test environment variable secrets provider."""
    # Set test environment variable
    os.environ["TEST_SECRET"] = "secret_value"

    provider = EnvironmentSecretsProvider(prefix="TEST_")
    secret = await provider.get_secret("SECRET")

    assert secret is not None
    assert secret.value == "secret_value"
    assert secret.source == "environment"

    # Cleanup
    del os.environ["TEST_SECRET"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_environment_secrets_provider_not_found():
    """Test environment provider with non-existent secret."""
    provider = EnvironmentSecretsProvider()
    secret = await provider.get_secret("NONEXISTENT_SECRET")

    assert secret is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_environment_secrets_provider_json():
    """Test environment provider with JSON secret."""
    import json

    test_data = {"key1": "value1", "key2": "value2"}
    os.environ["TEST_JSON"] = json.dumps(test_data)

    provider = EnvironmentSecretsProvider(prefix="TEST_")
    secret_dict = await provider.get_secret_dict("JSON")

    assert secret_dict == test_data

    # Cleanup
    del os.environ["TEST_JSON"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cached_secrets_provider():
    """Test cached secrets provider."""
    os.environ["CACHE_TEST"] = "cached_value"

    base_provider = EnvironmentSecretsProvider()
    cached_provider = CachedSecretsProvider(base_provider, cache_ttl=300)

    # First call - cache miss
    secret1 = await cached_provider.get_secret("CACHE_TEST")
    assert secret1.value == "cached_value"

    # Change environment variable
    os.environ["CACHE_TEST"] = "new_value"

    # Second call - should return cached value
    secret2 = await cached_provider.get_secret("CACHE_TEST")
    assert secret2.value == "cached_value"  # Still cached

    # Invalidate cache
    cached_provider.invalidate("CACHE_TEST")

    # Third call - should get new value
    secret3 = await cached_provider.get_secret("CACHE_TEST")
    assert secret3.value == "new_value"

    # Cleanup
    del os.environ["CACHE_TEST"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chained_secrets_provider():
    """Test chained secrets provider with fallback."""
    # Set secret in environment
    os.environ["CHAIN_SECRET"] = "env_value"

    # Create two providers
    provider1 = EnvironmentSecretsProvider(prefix="MISSING_")
    provider2 = EnvironmentSecretsProvider()

    # Chain them
    chained = ChainedSecretsProvider([provider1, provider2])

    # Should fall back to provider2
    secret = await chained.get_secret("CHAIN_SECRET")
    assert secret is not None
    assert secret.value == "env_value"

    # Cleanup
    del os.environ["CHAIN_SECRET"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_secrets_manager_get():
    """Test SecretsManager get method."""
    os.environ["MGR_SECRET"] = "manager_value"

    provider = EnvironmentSecretsProvider()
    manager = SecretsManager(provider)

    value = await manager.get("MGR_SECRET")
    assert value == "manager_value"

    # Test default value
    value = await manager.get("NONEXISTENT", default="default_val")
    assert value == "default_val"

    # Cleanup
    del os.environ["MGR_SECRET"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_secrets_manager_get_required():
    """Test SecretsManager get_required method."""
    os.environ["REQUIRED_SECRET"] = "required_value"

    provider = EnvironmentSecretsProvider()
    manager = SecretsManager(provider)

    value = await manager.get_required("REQUIRED_SECRET")
    assert value == "required_value"

    # Should raise ValueError for missing secret
    with pytest.raises(ValueError, match="Required secret.*not found"):
        await manager.get_required("NONEXISTENT")

    # Cleanup
    del os.environ["REQUIRED_SECRET"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_secrets_manager_get_int():
    """Test SecretsManager get_int method."""
    os.environ["INT_SECRET"] = "42"

    provider = EnvironmentSecretsProvider()
    manager = SecretsManager(provider)

    value = await manager.get_int("INT_SECRET")
    assert value == 42
    assert isinstance(value, int)

    # Cleanup
    del os.environ["INT_SECRET"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_secrets_manager_get_bool():
    """Test SecretsManager get_bool method."""
    provider = EnvironmentSecretsProvider()
    manager = SecretsManager(provider)

    # Test various true values
    for true_val in ["true", "True", "TRUE", "yes", "1"]:
        os.environ["BOOL_SECRET"] = true_val
        value = await manager.get_bool("BOOL_SECRET")
        assert value is True

    # Test various false values
    for false_val in ["false", "False", "FALSE", "no", "0"]:
        os.environ["BOOL_SECRET"] = false_val
        value = await manager.get_bool("BOOL_SECRET")
        assert value is False

    # Cleanup
    del os.environ["BOOL_SECRET"]


@pytest.mark.unit
def test_secret_value_repr():
    """Test SecretValue repr masks the actual value."""
    secret = SecretValue(
        key="api_key",
        value="super_secret_value_123",
        source="test",
        metadata={"extra": "data"}
    )

    repr_str = repr(secret)
    assert "api_key" in repr_str
    assert "test" in repr_str
    assert "super_secret_value_123" not in repr_str  # Value should be masked
    assert "***" in repr_str


@pytest.mark.unit
def test_secret_value_metadata_default():
    """Test SecretValue metadata defaults to empty dict."""
    secret = SecretValue(key="test", value="value", source="env")
    assert secret.metadata == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_environment_secrets_provider_with_prefix():
    """Test environment provider uses prefix correctly."""
    os.environ["MY_PREFIX_SECRET"] = "prefixed_value"
    os.environ["SECRET"] = "unprefixed_value"

    provider = EnvironmentSecretsProvider(prefix="MY_PREFIX_")

    # Should find with prefix
    secret = await provider.get_secret("SECRET")
    assert secret is not None
    assert secret.value == "prefixed_value"
    assert secret.metadata["env_key"] == "MY_PREFIX_SECRET"

    # Cleanup
    del os.environ["MY_PREFIX_SECRET"]
    del os.environ["SECRET"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_environment_secrets_provider_json_invalid():
    """Test environment provider handles invalid JSON gracefully."""
    os.environ["BAD_JSON"] = "{this is not valid json}"

    provider = EnvironmentSecretsProvider()
    secret_dict = await provider.get_secret_dict("BAD_JSON")

    assert secret_dict is None  # Should return None for invalid JSON

    # Cleanup
    del os.environ["BAD_JSON"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cached_secrets_provider_invalidate_all():
    """Test cached provider can invalidate entire cache."""
    os.environ["CACHE1"] = "value1"
    os.environ["CACHE2"] = "value2"

    base_provider = EnvironmentSecretsProvider()
    cached_provider = CachedSecretsProvider(base_provider)

    # Load both into cache
    await cached_provider.get_secret("CACHE1")
    await cached_provider.get_secret("CACHE2")

    # Change env vars
    os.environ["CACHE1"] = "new1"
    os.environ["CACHE2"] = "new2"

    # Invalidate all
    cached_provider.invalidate()

    # Should get new values
    secret1 = await cached_provider.get_secret("CACHE1")
    secret2 = await cached_provider.get_secret("CACHE2")
    assert secret1.value == "new1"
    assert secret2.value == "new2"

    # Cleanup
    del os.environ["CACHE1"]
    del os.environ["CACHE2"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cached_secrets_provider_dict():
    """Test cached provider caches get_secret_dict results."""
    import json

    test_data = {"key": "value"}
    os.environ["JSON_CACHE"] = json.dumps(test_data)

    base_provider = EnvironmentSecretsProvider()
    cached_provider = CachedSecretsProvider(base_provider)

    # First call
    dict1 = await cached_provider.get_secret_dict("JSON_CACHE")

    # Change env var
    os.environ["JSON_CACHE"] = json.dumps({"key": "new_value"})

    # Second call - should be cached
    dict2 = await cached_provider.get_secret_dict("JSON_CACHE")
    assert dict2 == test_data  # Still cached

    # Cleanup
    del os.environ["JSON_CACHE"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chained_secrets_provider_all_fail():
    """Test chained provider when all providers fail."""
    provider1 = EnvironmentSecretsProvider(prefix="MISSING1_")
    provider2 = EnvironmentSecretsProvider(prefix="MISSING2_")

    chained = ChainedSecretsProvider([provider1, provider2])

    secret = await chained.get_secret("NONEXISTENT")
    assert secret is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chained_secrets_provider_middle_success():
    """Test chained provider finds secret in middle provider."""
    os.environ["MIDDLE_SECRET"] = "found_it"

    provider1 = EnvironmentSecretsProvider(prefix="FIRST_")
    provider2 = EnvironmentSecretsProvider()  # This one will find it
    provider3 = EnvironmentSecretsProvider(prefix="THIRD_")

    chained = ChainedSecretsProvider([provider1, provider2, provider3])

    secret = await chained.get_secret("MIDDLE_SECRET")
    assert secret is not None
    assert secret.value == "found_it"

    # Cleanup
    del os.environ["MIDDLE_SECRET"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chained_secrets_provider_get_secret_dict():
    """Test chained provider with get_secret_dict."""
    import json

    test_data = {"chained": "dict"}
    os.environ["CHAIN_JSON"] = json.dumps(test_data)

    provider1 = EnvironmentSecretsProvider(prefix="MISSING_")
    provider2 = EnvironmentSecretsProvider()

    chained = ChainedSecretsProvider([provider1, provider2])

    secret_dict = await chained.get_secret_dict("CHAIN_JSON")
    assert secret_dict == test_data

    # Cleanup
    del os.environ["CHAIN_JSON"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_secrets_manager_get_dict():
    """Test SecretsManager get_dict method."""
    import json

    test_data = {"manager": "dict_value"}
    os.environ["MGR_DICT"] = json.dumps(test_data)

    provider = EnvironmentSecretsProvider()
    manager = SecretsManager(provider)

    result = await manager.get_dict("MGR_DICT")
    assert result == test_data

    # Test non-existent
    result = await manager.get_dict("NONEXISTENT")
    assert result is None

    # Cleanup
    del os.environ["MGR_DICT"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_secrets_manager_get_int_invalid():
    """Test SecretsManager get_int with invalid value."""
    os.environ["INVALID_INT"] = "not_a_number"

    provider = EnvironmentSecretsProvider()
    manager = SecretsManager(provider)

    # Should return default for invalid int
    value = await manager.get_int("INVALID_INT", default=99)
    assert value == 99

    # Should return None if no default
    value = await manager.get_int("INVALID_INT")
    assert value is None

    # Cleanup
    del os.environ["INVALID_INT"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_secrets_manager_get_int_missing():
    """Test SecretsManager get_int with missing secret."""
    provider = EnvironmentSecretsProvider()
    manager = SecretsManager(provider)

    value = await manager.get_int("MISSING_INT", default=42)
    assert value == 42


@pytest.mark.unit
@pytest.mark.asyncio
async def test_secrets_manager_get_bool_invalid():
    """Test SecretsManager get_bool with invalid value."""
    os.environ["INVALID_BOOL"] = "maybe"

    provider = EnvironmentSecretsProvider()
    manager = SecretsManager(provider)

    # Should return default for invalid bool
    value = await manager.get_bool("INVALID_BOOL", default=True)
    assert value is True

    # Should return None if no default
    value = await manager.get_bool("INVALID_BOOL")
    assert value is None

    # Cleanup
    del os.environ["INVALID_BOOL"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_secrets_manager_get_bool_missing():
    """Test SecretsManager get_bool with missing secret."""
    provider = EnvironmentSecretsProvider()
    manager = SecretsManager(provider)

    value = await manager.get_bool("MISSING_BOOL", default=False)
    assert value is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cached_secrets_provider_cache_miss():
    """Test cached provider returns None for cache miss."""
    base_provider = EnvironmentSecretsProvider()
    cached_provider = CachedSecretsProvider(base_provider)

    # Should return None for non-existent secret (not cached)
    secret = await cached_provider.get_secret("NONEXISTENT_KEY")
    assert secret is None

    secret_dict = await cached_provider.get_secret_dict("NONEXISTENT_DICT")
    assert secret_dict is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chained_secrets_provider_dict_all_fail():
    """Test chained provider get_secret_dict when all fail."""
    provider1 = EnvironmentSecretsProvider(prefix="MISSING1_")
    provider2 = EnvironmentSecretsProvider(prefix="MISSING2_")

    chained = ChainedSecretsProvider([provider1, provider2])

    secret_dict = await chained.get_secret_dict("NONEXISTENT")
    assert secret_dict is None
