from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "OK", "message": "Project running from D drive"}

@app.get("/check")
def check():
    return {
        "postgres": "running - check Docker Desktop green dots",
        "elasticsearch": "running - check Docker Desktop green dots",
        "project": "D:\\myproject"
    }
