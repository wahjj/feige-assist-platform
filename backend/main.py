from backend.feige.app import create_feige_app


create_app = create_feige_app
app = create_feige_app()

__all__ = ["app", "create_app", "create_feige_app"]
