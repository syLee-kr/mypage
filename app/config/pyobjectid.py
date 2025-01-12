from bson import ObjectId
from pydantic.json_schema import GetJsonSchemaHandler


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, field=None):  # field 추가
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("유효하지 않은 ObjectId입니다.")

    @classmethod
    def __get_pydantic_json_schema__(cls, handler: GetJsonSchemaHandler):
        return handler({"type": "string", "pattern": "^[a-fA-F0-9]{24}$"})
