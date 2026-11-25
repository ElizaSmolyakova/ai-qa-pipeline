from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Payment Mock Service")


class PayRequest(BaseModel):
    amount: float
    currency: str = "RUB"


@app.post("/api/v1/pay")
def process_payment(request: PayRequest):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="INVALID_AMOUNT")
    if request.currency != "RUB":
        raise HTTPException(status_code=422, detail="UNSUPPORTED_CURRENCY")
    if request.amount > 5000:
        return JSONResponse(status_code=202, content={"status": "3DS_REQUIRED", "amount": request.amount})

    return JSONResponse(status_code=200, content={"status": "SUCCESS", "amount": request.amount})
