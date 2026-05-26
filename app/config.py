from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_FROM_NUMBER: str
    RESEND_API_KEY: str
    MY_TEST_PHONE: str
    MY_TEST_EMAIL: str
    UPSTREAM_API_URL: str = "https://zz1mpoguje.execute-api.us-east-1.amazonaws.com/default/airline-assessment"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
