from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    llm_input_cost_per_1m: float | None = None
    llm_output_cost_per_1m: float | None = None

    class Config:
        env_file = ".env"


settings = Settings()
