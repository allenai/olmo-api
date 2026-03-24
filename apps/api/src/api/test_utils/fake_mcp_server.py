from typing import NoReturn

from pydantic_ai import FunctionToolset, ModelRetry, RunContext

test_toolset = FunctionToolset(max_retries=0)


@test_toolset.tool()
async def always_fails(ctx: RunContext) -> NoReturn:  # noqa: ARG001, RUF029
    raise ModelRetry("Always fails")  # noqa: EM101, TRY003


@test_toolset.tool()
async def celsius_to_fahrenheit(celsius: float) -> float:  # noqa: RUF029
    """Convert Celsius to Fahrenheit.

    Args:
        celsius: Temperature in Celsius

    Returns:
        Temperature in Fahrenheit
    """

    return (celsius * 9 / 5) + 32


@test_toolset.tool()
async def get_weather_forecast(location: str) -> str:  # noqa: RUF029
    """Get the weather forecast for a location.

    Args:
        location: The location to get the weather forecast for.

    Returns:
        The weather forecast for the location.
    """
    return f"The weather in {location} is sunny and 26 degrees Celsius."
