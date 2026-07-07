from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router as api_router
from app.database import engine, Base
from dotenv import load_dotenv
load_dotenv()  
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI数字人智慧景区导览系统",
    description="为游客提供智能导览服务，为管理员提供景区管理功能",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "AI数字人智慧景区导览系统后端服务"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)