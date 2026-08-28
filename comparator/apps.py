from django.apps import AppConfig


class ComparatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'comparator'

    def ready(self):
        import os
        # Render Free Tier RAM is strictly limited to 512MB. 
        # Bypassing PyTorch prevents the container from crash-looping due to Out Of Memory (OOM) SIGKILLs.
        if os.environ.get('RENDER_EXTERNAL_HOSTNAME') and not os.environ.get('ENABLE_TRANSFORMERS'):
            print("--- RENDER FREE TIER DETECTED: BYPASSING PYTORCH PRELOAD TO PREVENT OOM ---")
            return

        # Pre-load embedding model on startup in the main thread/process
        if os.environ.get('RUN_MAIN') == 'true' or 'test' in os.sys.argv or os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
            try:
                from .utils import get_embedding_model
                print("--- PRE-LOADING EMBEDDING MODEL START ---")
                get_embedding_model()
                print("--- PRE-LOADING EMBEDDING MODEL SUCCESSFUL ---")
            except Exception as e:
                print(f"Error pre-loading embedding model: {e}")

