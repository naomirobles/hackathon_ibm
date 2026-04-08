from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    watsonx_api_key: str = ""
    watsonx_project_id: str = ""
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"
    nominatim_user_agent: str = "señalcdmx-hackathon"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
