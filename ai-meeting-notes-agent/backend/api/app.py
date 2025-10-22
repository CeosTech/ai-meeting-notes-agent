from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()


@app.get("/-/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


class SummReq(BaseModel):
    text: str


@app.post("/summarize")
async def summarize(req: SummReq) -> dict[str, str]:
    snippet = req.text[:120]
    return {"summary": f"Summary of: {snippet}..."}
