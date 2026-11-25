from pydantic import BaseModel, Field


class TestCase(BaseModel):
    title: str = Field(description="Короткое название тест-кейса на русском")
    is_negative: bool = Field(description="True если негативный сценарий, иначе False")
    http_method: str = Field(description="HTTP метод из требований: GET, POST, PUT или DELETE")
    endpoint: str = Field(description="Только путь эндпоинта без метода, например /api/v1/pay")
    expected_status: int = Field(description="Ожидаемый HTTP статус-код")


class TestSuite(BaseModel):
    cases: list[TestCase]

class GeneratedCode(BaseModel):
    python_code: str