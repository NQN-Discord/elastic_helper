import argparse
import asyncio

from elastic_helper import ElasticSearchClient

parser = argparse.ArgumentParser()
parser.add_argument("--elasticsearch", dest="elasticsearch", required=True)
command_parser = parser.add_subparsers(dest="command")
init_parser = command_parser.add_parser("init")


async def run_init(elasticsearch_uri: str):
    print("Initialising elasticsearch...")
    elastic = ElasticSearchClient([elasticsearch_uri])
    async with elastic as db:
        print("Elastic info:", await db.get_info())
        await db.init_models()
    print("Initialisation complete")


async def main():
    args = parser.parse_args()
    match args.command:
        case "init":
            await run_init(args.elasticsearch)
        case _:
            raise AssertionError("Command not found!")


if __name__ == "__main__":
    asyncio.run(main())
