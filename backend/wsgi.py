from app.factory import create_app, start_scheduler

app = create_app()
start_scheduler(app)
