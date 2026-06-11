# OLIMPO Backend Deployment (Render)

Service Type:
Web Service

Build Command

pip install -r requirements.txt

Start Command

alembic upgrade head && uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT

Environment

Production

Primary URL

https://olimpo-backend.onrender.com
