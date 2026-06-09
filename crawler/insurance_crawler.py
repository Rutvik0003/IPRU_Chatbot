import asyncio
import os

from collections import deque
from urllib.parse import urljoin
from urllib.parse import urldefrag

import aiohttp

from bs4 import BeautifulSoup

from crawler.config import *
from crawler.downloader import download_pdf
from crawler.logger import logger
from crawler.utils import is_same_domain

from shared.file_filter import (
    should_reject_file,
    is_priority_insurance_file
)


class InsuranceCrawler:

    def __init__(self, company_name, start_url):

        self.company_name = company_name
        self.start_url = start_url

        self.visited = set()
        self.pdfs = set()

        self.pages_crawled = 0
        self.errors = 0

        # Stats
        self.rejected_by_rule = 0
        self.priority_files = 0

    async def fetch(self, session, url):

        try:

            async with session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                ssl=False
            ) as response:

                if response.status != 200:

                    logger.warning(
                        f"Non-200 status "
                        f"{response.status} for {url}"
                    )

                    return None, None

                content_type = response.headers.get(
                    "Content-Type",
                    ""
                ).lower()

                # Direct PDF detection
                if "application/pdf" in content_type:

                    return "PDF", response

                # Skip non-html content
                if "text/html" not in content_type:

                    return None, None

                html = await response.text(
                    errors="ignore"
                )

                return html, response

        except Exception as e:

            self.errors += 1

            logger.error(
                f"Fetch failed {url}: {e}"
            )

            return None, None

    async def process_pdf_link(
        self,
        session,
        pdf_url
    ):

        try:

            filename = os.path.basename(
                pdf_url
            ).lower()

            # -------------------------
            # RULE-BASED REJECTION
            # -------------------------

            if should_reject_file(
                filename
            ):

                self.rejected_by_rule += 1

                print(
                    f"[RULE REJECTED] "
                    f"{filename}"
                )

                logger.info(
                    f"Rejected by filename rule: "
                    f"{filename}"
                )

                return

            # -------------------------
            # PRIORITY INSURANCE FILE
            # -------------------------

            if is_priority_insurance_file(
                filename
            ):

                self.priority_files += 1

                print(
                    f"[PRIORITY PDF] "
                    f"{filename}"
                )

            # -------------------------
            # DOWNLOAD PDF
            # -------------------------

            await download_pdf(
                pdf_url,
                self.company_name
            )

        except Exception as e:

            self.errors += 1

            logger.error(
                f"PDF processing failed "
                f"for {pdf_url}: {e}"
            )

    async def crawl(self):

        timeout = aiohttp.ClientTimeout(
            total=REQUEST_TIMEOUT
        )

        connector = aiohttp.TCPConnector(
            limit=MAX_CONCURRENT_REQUESTS,
            ssl=False
        )

        async with aiohttp.ClientSession(
            connector=connector,
            headers=HEADERS,
            timeout=timeout,
            max_line_size=65536,
            max_field_size=65536
        ) as session:

            queue = deque([
                (self.start_url, 0)
            ])

            while queue:

                current_url, depth = queue.popleft()

                current_url = urldefrag(
                    current_url
                )[0]

                # Skip visited
                if current_url in self.visited:
                    continue

                # Depth control
                if depth > MAX_DEPTH:
                    continue

                self.visited.add(
                    current_url
                )

                self.pages_crawled += 1

                print(
                    f"[{self.company_name}] "
                    f"Pages: {self.pages_crawled} | "
                    f"PDFs: {len(self.pdfs)} | "
                    f"Rejected: {self.rejected_by_rule} | "
                    f"Priority: {self.priority_files} | "
                    f"Queue: {len(queue)} | "
                    f"Current: {current_url}"
                )

                html, response = await self.fetch(
                    session,
                    current_url
                )

                if not html:
                    continue

                # Direct PDF response
                if html == "PDF":

                    if current_url not in self.pdfs:

                        self.pdfs.add(
                            current_url
                        )

                        await self.process_pdf_link(
                            session,
                            current_url
                        )

                    continue

                try:

                    soup = BeautifulSoup(
                        html,
                        "lxml"
                    )

                except Exception as e:

                    self.errors += 1

                    logger.error(
                        f"BeautifulSoup parsing failed "
                        f"for {current_url}: {e}"
                    )

                    continue

                tasks = []

                for tag in soup.find_all(
                    "a",
                    href=True
                ):

                    try:

                        href = tag["href"].strip()

                        if not href:
                            continue

                        absolute_url = urljoin(
                            current_url,
                            href
                        )

                        absolute_url = urldefrag(
                            absolute_url
                        )[0]

                        # Restrict to same domain
                        if not is_same_domain(
                            self.start_url,
                            absolute_url
                        ):
                            continue

                        # Ignore unsupported links
                        if absolute_url.startswith(
                            (
                                "mailto:",
                                "javascript:",
                                "tel:"
                            )
                        ):
                            continue

                        # Fast PDF detection
                        is_pdf_url = (
                            ".pdf"
                            in absolute_url.lower()
                        )

                        if is_pdf_url:

                            if absolute_url not in self.pdfs:

                                self.pdfs.add(
                                    absolute_url
                                )

                                tasks.append(
                                    self.process_pdf_link(
                                        session,
                                        absolute_url
                                    )
                                )

                        else:

                            if absolute_url not in self.visited:

                                queue.append(
                                    (
                                        absolute_url,
                                        depth + 1
                                    )
                                )

                    except Exception as e:

                        self.errors += 1

                        logger.error(
                            f"Link processing failed "
                            f"on {current_url}: {e}"
                        )

                        continue

                if tasks:

                    await asyncio.gather(
                        *tasks,
                        return_exceptions=True
                    )

        summary = (
            f"\n========== COMPLETED ==========\n"
            f"Company: {self.company_name}\n"
            f"Pages Crawled: {self.pages_crawled}\n"
            f"PDFs Found: {len(self.pdfs)}\n"
            f"Rejected By Rules: {self.rejected_by_rule}\n"
            f"Priority PDFs: {self.priority_files}\n"
            f"Errors: {self.errors}\n"
            f"================================\n"
        )

        print(summary)

        logger.info(summary)