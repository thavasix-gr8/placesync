from pydantic import BaseModel, ConfigDict, Field


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=6)
    register_number: str
    department: str
    batch: str
    cgpa: float = Field(ge=0, le=10)
    arrears: int = Field(ge=0)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    register_number: str
    department: str
    batch: str
    cgpa: float
    arrears: int

    model_config = ConfigDict(from_attributes=True)
