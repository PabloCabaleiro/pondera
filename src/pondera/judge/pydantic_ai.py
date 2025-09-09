"""
Core agent implementation providing model selection and configuration for AI agents.
"""

from types import NoneType
from typing import Any

from openai import AsyncAzureOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.bedrock import BedrockProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits

from pondera.settings import get_settings


def _get_model_anthropic(
    model_name: str | None = None, anthropic_api_key: str | None = None
) -> AnthropicModel:
    """Create Anthropic model instance."""
    settings = get_settings()
    anthropic_api_key = anthropic_api_key or settings.anthropic_api_key
    model_name = model_name or "claude-3-5-sonnet-20241022"  # Default Anthropic model

    assert anthropic_api_key, "ANTHROPIC_API_KEY is not set"
    assert model_name, "Model name is not set"

    provider = AnthropicProvider(api_key=anthropic_api_key)
    return AnthropicModel(model_name=model_name, provider=provider)


def _get_model_bedrock(
    model_name: str | None = None, aws_region: str | None = None
) -> BedrockConverseModel:
    """Create Bedrock model instance."""
    settings = get_settings()
    model_name = model_name or settings.bedrock_model_name
    aws_region = aws_region or settings.aws_region

    assert model_name, "BEDROCK_MODEL_NAME is not set"
    assert aws_region, "AWS_REGION is not set"

    if settings.aws_profile is not None:
        return BedrockConverseModel(model_name=model_name)

    provider = BedrockProvider(region_name=aws_region)
    return BedrockConverseModel(model_name=model_name, provider=provider)


def _get_model_ollama(
    model_name: str | None = None, ollama_url: str | None = None
) -> OpenAIChatModel:
    """Create Ollama model instance."""
    settings = get_settings()
    ollama_url = ollama_url or settings.ollama_url
    model_name = model_name or settings.ollama_model_name

    assert ollama_url, "OLLAMA_URL is not set"
    assert model_name, "Model name is not set"

    provider = OpenAIProvider(base_url=ollama_url)
    return OpenAIChatModel(model_name=model_name, provider=provider)


def _get_model_openai(
    model_name: str | None = None, openai_api_key: str | None = None
) -> OpenAIChatModel:
    """Create OpenAI model instance."""
    settings = get_settings()
    openai_api_key = openai_api_key or settings.openai_api_key
    model_name = model_name or settings.openai_model_name

    assert openai_api_key, "OPENAI_API_KEY is not set"
    assert model_name, "Model name is not set"

    provider = OpenAIProvider(api_key=openai_api_key)
    return OpenAIChatModel(model_name=model_name, provider=provider)


def _get_model_openai_azure(
    model_name: str | None = None,
    azure_openai_api_key: str | None = None,
    azure_openai_endpoint: str | None = None,
    azure_openai_api_version: str | None = None,
) -> OpenAIChatModel:
    """Create Azure OpenAI model instance."""
    settings = get_settings()
    model_name = model_name or settings.azure_model_name
    azure_openai_api_key = azure_openai_api_key or settings.azure_openai_api_key
    azure_openai_endpoint = azure_openai_endpoint or settings.azure_openai_endpoint
    azure_openai_api_version = azure_openai_api_version or settings.azure_openai_api_version

    assert azure_openai_endpoint, "AZURE_OPENAI_ENDPOINT is not set"
    assert azure_openai_api_key, "AZURE_OPENAI_API_KEY is not set"
    assert azure_openai_api_version, "AZURE_OPENAI_API_VERSION is not set"
    assert model_name, "Model name is not set"

    client = AsyncAzureOpenAI(
        azure_endpoint=azure_openai_endpoint,
        api_version=azure_openai_api_version,
        api_key=azure_openai_api_key,
    )
    return OpenAIChatModel(model_name=model_name, provider=OpenAIProvider(openai_client=client))


def _get_model_open_router(
    model_name: str | None = None,
    openrouter_api_url: str | None = None,
    openrouter_api_key: str | None = None,
) -> OpenAIChatModel:
    """Create OpenRouter model instance."""
    settings = get_settings()
    model_name = model_name or settings.openrouter_model_name
    openrouter_api_url = openrouter_api_url or settings.openrouter_api_url
    openrouter_api_key = openrouter_api_key or settings.openrouter_api_key

    assert openrouter_api_url, "OPENROUTER_API_URL is not set"
    assert openrouter_api_key, "OPENROUTER_API_KEY is not set"
    assert (
        model_name
    ), "Model name is not set, missing 'OPENROUTER_MODEL_NAME' environment variable?"

    provider = OpenAIProvider(base_url=openrouter_api_url, api_key=openrouter_api_key)
    return OpenAIChatModel(model_name, provider=provider)


def get_model(
    model_family: str | None = None, model_name: str | None = None, **kwargs: Any
) -> AnthropicModel | BedrockConverseModel | OpenAIChatModel:
    """Create and return appropriate model instance based on specified family and name."""
    settings = get_settings()
    model_family = model_family or settings.model_family

    assert (
        model_family is not None and model_family != ""
    ), f"Model family '{model_family}' is not set"

    match model_family:
        case "anthropic":
            return _get_model_anthropic(model_name=model_name, **kwargs)
        case "azure":
            return _get_model_openai_azure(model_name=model_name, **kwargs)
        case "bedrock":
            return _get_model_bedrock(model_name=model_name, **kwargs)
        case "ollama":
            return _get_model_ollama(model_name=model_name, **kwargs)
        case "openai":
            return _get_model_openai(model_name=model_name, **kwargs)
        case "openrouter":
            return _get_model_open_router(model_name=model_name, **kwargs)
        case _:
            raise ValueError(f"Model family '{model_family}' not supported")


def get_agent(
    model: AnthropicModel | BedrockConverseModel | OpenAIChatModel | None = None,
    *,
    instructions: str | None = None,
    system_prompt: str | tuple[str, ...] = (),
    tools: tuple[Any, ...] = (),
    toolsets: tuple[Any, ...] = (),
    model_settings: ModelSettings | None = None,
    output_type: Any = str,
    deps_type: type = NoneType,
) -> Agent:
    """Get a PydanticAI agent"""
    settings = get_settings()

    if model_settings is None:
        model_settings = ModelSettings(timeout=settings.model_timeout)
    if model is None:
        model = get_model()

    agent = Agent(
        model=model,
        output_type=output_type,
        instructions=instructions,
        system_prompt=system_prompt,
        deps_type=deps_type,
        model_settings=model_settings,
        tools=tools,
        toolsets=toolsets,
        instrument=True,
    )
    return agent


async def run_agent(
    agent: Agent,
    prompt: str | list[str],
    usage_limits: UsageLimits | None = None,
    verbose: bool = False,
    debug: bool = False,
    log_model_requests: bool = False,
    parent_logger: Any | None = None,
) -> tuple[Any, list[Any]]:
    """Query the LLM"""
    # Results
    nodes, result = [], None
    async with agent.iter(prompt, usage_limits=usage_limits) as agent_run:
        # Note: Logging functionality would need to be implemented based on available libraries
        # For now, we'll just collect nodes and return result
        async for node in agent_run:
            if verbose or debug:
                print(f"Agent node: {node}")
            nodes.append(node)
        result = agent_run.result
    return result.output if result else None, nodes
