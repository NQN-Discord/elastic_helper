from typing import List, Dict, NoReturn, Any, Type, Optional, Generator
from logging import getLogger
from prometheus_client import Counter

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError

from elasticsearch.helpers import async_bulk, async_scan
from .models import *

log = getLogger(__name__)

search_request = Counter(
    "elastic_search_total",
    "Searches",
    ["model"],
    namespace="elastic_helper"
)
get_request = Counter(
    "elastic_get_total",
    "Gets",
    ["model"],
    namespace="elastic_helper"
)
patch_request = Counter(
    "elastic_patch_total",
    "Modifications",
    ["op_type"],
    namespace="elastic_helper"
)


class ElasticSearchClient:
    def __init__(self, hosts):
        self.hosts = hosts
        self._db = None
        self._alive = 0
        self._has_waited = False

    async def __aenter__(self):
        if self._alive == 0:
            _db = _ElasticSearchDB(self.hosts)
            if not self._has_waited:
                await _db._client.cluster.health(wait_for_status="yellow")
                self._has_waited = True
            self._db = _db
        self._alive += 1
        return self._db

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._alive -= 1
        if self._alive == 0:
            await self._db.close()
        return False


class _ElasticSearchDB:
    def __init__(self, hosts):
        self._client = AsyncElasticsearch(hosts=hosts, maxsize=40)

    async def get_info(self):
        return await self._client.info()

    async def get_stats(self):
        return await self._client.transport.perform_request("GET", "/_nodes/stats")

    async def close(self):
        await self._client.transport.close()

    async def init_models(self):
        for model in {GuildGroup, Group, ExtraEmote, Sticker, Logging, GuildMessage}:
            if "*" in model.index:
                await self._client.indices.put_index_template(model.index.replace("*", "_"), body={
                    "template": model.elastic_setup(),
                    "index_patterns": model.index
                })
            elif not await self._client.indices.exists(index=model.index):
                await self._client.indices.create(model.index, body=model.elastic_setup())

    async def get(self, model: Type[Model], id: str) -> Optional[Model]:
        log.info("Getting a %s model", model.__name__)
        get_request.labels(model=model.__name__).inc()
        index = model.index
        try:
            i = await self._client.get(index, id)
        except NotFoundError:
            return None
        return model(_id=i["_id"], _typecheck=False, **i["_source"])

    async def bulk_get(self, model: Type[Model], ids: List[str]) -> List[Model]:
        log.info("Bulk getting %s %s models", len(ids), model.__name__)
        get_request.labels(model=model.__name__).inc(len(ids))
        models = (await self._client.mget(index=model.index, body={"ids": ids}))["docs"]
        return [model(_id=i["_id"], _typecheck=False, **i["_source"]) for i in models]

    async def search(self, model: Type[Model], no_results: int, offset: int = 0, query_type="match", query=None, sort=None, **kwargs):
        log.info("Searching for %s models", model.__name__)
        search_request.labels(model=model.__name__).inc()
        index = model.index
        if query is None:
            query = {}
            if kwargs:
                query = {"query": {"bool": {"must": [{query_type: {name: value}} for name, value in kwargs.items() if value is not None]}}}
        if sort is not None:
            query["sort"] = sort
        results: Dict[str, Any] = (await self._client.search(
            index=index,
            body=query,
            size=no_results,
            from_=offset
        ))["hits"]
        converted = []
        for i in results["hits"]:
            converted.append(model(_id=i["_id"], _typecheck=False, **i["_source"]))
        return results["total"]["value"], converted

    async def search_single(self, model: Type[Model], **kwargs) -> Optional[Model]:
        no_results, models = await self.search(model, no_results=1, **kwargs)
        if no_results == 0:
            return
        return models[0]

    def _add_elastic(self, serialised, model: Model, op_type: str):
        index = model.index
        if "time" in serialised:
            try:
                date = serialised["time"].date().isoformat()
            except AttributeError:
                date = serialised["time"].split("T", 1)[0]
            index = index.replace("*", date)
        return {
            "_op_type": op_type,
            "_index": index,
            **serialised
        }

    def bulk_serialise(self, model: Model, op_type: str = "create"):
        return self._add_elastic(model.serialise(), model, op_type)

    async def bulk_add_serialised(self, serialised: Generator, chunk_size: int = 10000):
        await async_bulk(
            self._client,
            serialised,
            chunk_size=chunk_size,
        )

    async def bulk_add(self, models: List[Model], chunk_size: int = 10000, op_type: str = "create") -> NoReturn:
        if len(models) == 0:
            return
        log.info("Adding %s models", len(models))
        patch_request.labels(op_type=op_type).inc(len(models))
        await self.bulk_add_serialised(
            (self.bulk_serialise(model, op_type) for model in models),
            chunk_size=chunk_size
        )

    async def add(self, model: Model, op_type: str = "create") -> NoReturn:
        await self.bulk_add([model], op_type=op_type)

    async def delete(self, model: Model) -> NoReturn:
        try:
            patch_request.labels(op_type="delete").inc()
            await self._client.delete(index=model.index, id=model._id)
        except NotFoundError:
            pass

    async def delete_id(self, model: Type[Model], id: str):
        try:
            patch_request.labels(op_type="delete").inc()
            await self._client.delete(index=model.index, id=id)
        except NotFoundError:
            pass

    async def bulk_delete(self, models: List[Model]):
        return await self.bulk_add(models, op_type="delete")

    async def scroll(self, model: Type[Model], **kwargs):
        async for i in async_scan(self._client, index=model.index, **kwargs):
            yield model(
                _id=i["_id"],
                _typecheck=False,
                **i["_source"]
            )
