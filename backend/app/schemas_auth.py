from pydantic import BaseModel, Field


class MicrosoftTokenRequest(BaseModel):
    id_token: str = Field(min_length=20, max_length=20000)
