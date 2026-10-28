from fastapi import FastAPI
app = FastAPI(title="Gateway")
@app.get("/")
def root(): return {"status": "gateway ok"}