from fastapi import FastAPI
app = FastAPI(title="Metadata Service")
@app.get("/")
def root(): return {"status": "metadata ok"}
@app.post("/heartbeat")
def heartbeat(data: dict): print(f"Heartbeat: {data}"); return {"ok": True}