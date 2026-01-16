try:
    from typing import GenericMeta
except ImportError:
    from typing import _GenericAlias
    py37 = True
else:
    py37 = False

from typing import Type, Dict, List, Set
from uuid import uuid4

from oauth_helper.get_params import typecheck_class, is_namedtuple, typecheck_single

_model_cache: Dict[Type, Set[str]] = {}


class Model:
    index: str = NotImplemented
    initialise = {}

    def __init__(self, _id: str = None, _typecheck=True, **kwargs):
        if _id is None:
            _id = uuid4().hex
        if _typecheck:
            typecheck_class(kwargs, self.__class__.__annotations__)
        self._attrs = kwargs
        self._attrs["_id"] = _id

    def __repr__(self):
        return f"{self.__class__.__name__}({self._attrs})"

    def __setattr__(self, key, value):
        if key not in self.__class__.__annotations__:
            return super().__setattr__(key, value)
        typecheck_single(value, self.__class__.__annotations__[key], False)
        self._attrs[key] = value

    def __getattr__(self, item):
        if item.startswith("__"):
            return super().__getattr__(item)
        elif item == "_id":
            return self._attrs["_id"]
        elif item not in self.__class__.__annotations__:
            return super().__getattribute__(item)
        t = self.__class__.__annotations__[item]
        if is_namedtuple(t):
            return t(**self._attrs[item])

        if not py37:
            if isinstance(t, GenericMeta):
                if t.__origin__ is List:
                    of, = t.__args__
                    if is_namedtuple(of):
                        return [of(**i) for i in self._attrs[item]]
        else:
            if isinstance(t, _GenericAlias):
                if t._name == "List":
                    of, = t.__args__
                    if is_namedtuple(of):
                        return [of(**i) for i in self._attrs[item]]
        return self._attrs.get(item)

    def __hash__(self):
        # Never keep the value returned by this for longer than the object exists
        return hash(id(self))

    def serialise(self):
        return self._attrs

    @classmethod
    def elastic_setup(cls):
        return cls.initialise
