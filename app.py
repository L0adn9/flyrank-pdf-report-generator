from fastapi import FastAPI

app = FastAPI(title="PDF report generator", version="1.0")


@app.get("/health")
def health():
    return {"status": "ok"}
