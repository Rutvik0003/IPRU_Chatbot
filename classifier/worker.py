import asyncio

from classifier.pipeline import (
    process_pdf
)

from shared.queue_manager import (
    pdf_queue
)


REQUEST_DELAY = 5


async def classifier_worker(worker_id):

    while True:

        pdf_path = await pdf_queue.get()

        try:

            print(
                f"[Worker {worker_id}] "
                f"Processing: {pdf_path}"
            )

            await asyncio.to_thread(
                process_pdf,
                pdf_path
            )

            # Throttle requests
            await asyncio.sleep(
                REQUEST_DELAY
            )

        except Exception as e:

            print(
                f"[Worker {worker_id}] Error: {e}"
            )

        finally:

            pdf_queue.task_done()