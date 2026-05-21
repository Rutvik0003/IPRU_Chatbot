import aiofiles
import aiohttp
import os
from tenacity import retry, stop_after_attempt, wait_fixed

from utils import sanitize_filename
from logger import logger

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def download_pdf(session, pdf_url, company_name):
    try:
        async with session.get(pdf_url, timeout=60) as response:

            if response.status != 200:
                return

            content_type = response.headers.get("Content-Type", "")

            if "pdf" not in content_type.lower():
                return

            filename = pdf_url.split("/")[-1]

            if not filename.endswith(".pdf"):
                filename += ".pdf"

            filename = sanitize_filename(filename)

            folder = f"data/raw/{company_name}"
            os.makedirs(folder, exist_ok=True)

            filepath = os.path.join(folder, filename)

            if os.path.exists(filepath):
                logger.info(f"Already exists: {filepath}")
                return

            async with aiofiles.open(filepath, "wb") as f:
                await f.write(await response.read())

            print(
                f"[DOWNLOADED] "
                f"{company_name} -> "
                f"{filename}"
            )

            logger.info(f"Downloaded: {pdf_url}")

    except Exception as e:
        logger.error(f"PDF download failed {pdf_url}: {e}")