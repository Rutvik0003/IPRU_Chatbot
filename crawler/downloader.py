import os

import aiofiles
from curl_cffi import requests as cffi_requests
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_fixed

from crawler.utils import sanitize_filename
from crawler.logger import logger
from shared.queue_manager import pdf_queue


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2)
)
async def download_pdf(
    pdf_url: str,
    company_name: str
):
    try:
        async with cffi_requests.AsyncSession(
            impersonate="chrome120"
        ) as session:

            r = await session.get(
                pdf_url,
                timeout=60
            )

        if r.status_code != 200:
            return

        content_type = r.headers.get(
            "Content-Type", ""
        ).lower()

        if "pdf" not in content_type and not pdf_url.lower().endswith(".pdf"):
            return

        filename = pdf_url.split("/")[-1]

        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        filename = sanitize_filename(filename)

        folder = f"data/raw/{company_name}"
        os.makedirs(folder, exist_ok=True)

        filepath = os.path.join(folder, filename)

        if os.path.exists(filepath):
            return

        async with aiofiles.open(filepath, "wb") as f:
            await f.write(r.content)

        print(
            f"[DOWNLOADED] "
            f"{company_name} -> {filename}"
        )

        logger.info(f"Downloaded: {pdf_url}")

        await pdf_queue.put(filepath)

        print(f"[QUEUED] {filename}")

    except Exception as e:

        logger.error(
            f"PDF download failed {pdf_url}: {e}"
        )
