import asyncio
import yaml

from crawler import InsuranceCrawler

def load_yaml():
    with open("config/insurers.yaml", "r") as f:
        return yaml.safe_load(f)

async def run():

    config = load_yaml()

    tasks = []

    for company in config["companies"]:

        crawler = InsuranceCrawler(
            company["name"],
            company["url"]
        )

        tasks.append(crawler.crawl())

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(run())