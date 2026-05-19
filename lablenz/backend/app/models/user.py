from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    first_name: str = Field(max_length=50)
    middle_name: str | None = Field(default=None, max_length=50)
    last_name: str = Field(max_length=50)
    username: str
    email: str
    role: str = "user"  # Default role is 'user'