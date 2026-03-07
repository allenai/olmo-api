from pydantic_ai import FunctionToolset

test_toolset = FunctionToolset()


@test_toolset.tool()
async def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit.

    Args:
        celsius: Temperature in Celsius

    Returns:
        Temperature in Fahrenheit
    """
    return (celsius * 9 / 5) + 32


@test_toolset.tool()
async def get_weather_forecast(location: str) -> str:
    """Get the weather forecast for a location.

    Args:
        location: The location to get the weather forecast for.

    Returns:
        The weather forecast for the location.
    """
    return f"The weather in {location} is sunny and 26 degrees Celsius."
