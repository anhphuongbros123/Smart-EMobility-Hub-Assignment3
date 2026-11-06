from fastapi import FastAPI

import app.entities as _entities  
from app.boundaries.simulation_api import router as simulation_router
from app.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart E-Mobility Hub")
app.include_router(simulation_router)
#add your routers here with app.include_router(...)