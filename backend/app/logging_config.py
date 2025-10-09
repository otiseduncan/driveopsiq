import logging, sys
from pythonjsonlogger import jsonlogger

def setup_json_logging(level="INFO"):
    handler = logging.StreamHandler(sys.stdout)
    fmt = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d"
    )
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)