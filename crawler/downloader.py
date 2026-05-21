import os
import aiofiles
import aiohttp

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
    session,
    pdf_url,
    company_name
):

    try:

        async with session.get(
            pdf_url,
            timeout=60,
            allow_redirects=True,
            ssl=False
        ) as response:

            if response.status != 200:
                return

            content_type = response.headers.get(
                "Content-Type",
                ""
            ).lower()

            if "pdf" not in content_type:
                return

            filename = pdf_url.split("/")[-1]

            if not filename.endswith(".pdf"):
                filename += ".pdf"

            filename = sanitize_filename(filename)

            folder = f"data/raw/{company_name}"

            os.makedirs(folder, exist_ok=True)

            filepath = os.path.join(
                folder,
                filename
            )

            # Skip duplicate
            if os.path.exists(filepath):
                return

            async with aiofiles.open(
                filepath,
                "wb"
            ) as f:

                await f.write(
                    await response.read()
                )

            print(
                f"[DOWNLOADED] "
                f"{company_name} -> {filename}"
            )

            logger.info(
                f"Downloaded: {pdf_url}"
            )

            # Queue for classification
            await pdf_queue.put(filepath)

            print(
                f"[QUEUED] "
                f"{filename}"
            )

    except Exception as e:

        logger.error(
            f"PDF download failed {pdf_url}: {e}"
        )