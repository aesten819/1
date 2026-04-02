from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from stocks import search_stocks

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/api/search")
def api_search(q: str = ""):
    return search_stocks(q)
