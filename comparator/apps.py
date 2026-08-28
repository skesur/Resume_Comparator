from django.apps import AppConfig


class ComparatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'comparator'

    def ready(self):
        import os
        # Pre-load embedding model on startup in the main thread/process
        # This keeps the server request processing time near-instant.
        if os.environ.get('RUN_MAIN') == 'true' or 'test' in os.sys.argv:
            try:
                from .utils import get_embedding_model
                print("--- PRE-LOADING EMBEDDING MODEL START ---")
                get_embedding_model()
                print("--- PRE-LOADING EMBEDDING MODEL SUCCESSFUL ---")
            except Exception as e:
                print(f"Error pre-loading embedding model: {e}")

