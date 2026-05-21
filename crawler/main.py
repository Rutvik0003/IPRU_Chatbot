import asyncio
import yaml

from crawler.insurance_crawler import (
    InsuranceCrawler
)

from classifier.worker import (
    classifier_worker
)

from shared.queue_manager import (
    pdf_queue
)


def load_yaml():

    with open(
        "config/insurers.yaml",
        "r"
    ) as f:

        return yaml.safe_load(f)


async def run():

    config = load_yaml()

    crawler_tasks = []

    # Start classifier workers
    worker_tasks = [

        asyncio.create_task(
            classifier_worker(i)
        )

        for i in range(1)
    ]

    print(
        "\nStarted classifier workers\n"
    )

    # Start crawlers
    for company in config["companies"]:

        crawler = InsuranceCrawler(
            company["name"],
            company["url"]
        )

        crawler_tasks.append(

            asyncio.create_task(
                crawler.crawl()
            )
        )

    # Wait for all crawlers
    await asyncio.gather(
        *crawler_tasks
    )

    print(
        "\nCrawling completed\n"
    )

    # Wait until all queued PDFs processed
    await pdf_queue.join()

    print(
        "\nAll PDFs classified\n"
    )

    # Stop workers
    for worker in worker_tasks:

        worker.cancel()

    print(
        "\nALL TASKS COMPLETED\n"
    )


if __name__ == "__main__":

    asyncio.run(run())