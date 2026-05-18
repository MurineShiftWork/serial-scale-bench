from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Define which origins are allowed to make cross-origin requests
origins = [
    "http://localhost:*/*",          # local Dash UI during dev
    "http://127.0.0.1:*/*",          # another local variant
    # "https://ui.labwatch.org",        # production Dash UI
]

# Apply CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # use ["*"] for testing, restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/hello")
def read_hello():
    return {"msg": "Hello from the scale agent!"}

# If this file is run directly, start the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
