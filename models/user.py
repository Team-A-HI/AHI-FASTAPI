from pydantic import BaseModel, Field
import uuid # for _id universal unique indentify
from typing import Optional



class UserSchema(BaseModel):
    id: str = Field(default_factory=uuid.uuid4, alias="_id")
    name: str = Field(...)
    email: str = Field(...)
    password: str = Field(...)

    class Config:
        # for demo data to help the user schema to mongdb
        json_schema_extra = {
            "example":{
                "_id":"12345-45678-4562345-43",
                "name":"Dahee",
                "email":"test@test.com",
                "password":"dahee123"
            }
        }

# for update user class
class UpdateUsersSchema(BaseModel):
    name: Optional[str]
    email: Optional[str]
    password: Optional[str]

    class Config:
        # for demo data to help the user schema to mongdb
        json_schema_extra = {
            "example":{
                "name":"Dahee",
                "email":"test@test.com",
                "password":"dahee123"
            }
        }