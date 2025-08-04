from fastapi import FastAPI

__version__ = "0.0.1"

app = FastAPI()

@app.get("/")
def read_root():
    return {"AICO backend": f"running (version {__version__})"}
