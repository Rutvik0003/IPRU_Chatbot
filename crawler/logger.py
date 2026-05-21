import logging
import os

os.makedirs("data/logs", exist_ok=True)

logging.basicConfig(
    filename="data/logs/crawler.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)