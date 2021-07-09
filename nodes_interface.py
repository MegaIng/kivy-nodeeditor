from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, TypeVar, Union, Literal, TYPE_CHECKING, Any, Optional, Callable

if TYPE_CHECKING:
    from typing import TypeAlias

JSONData: TypeAlias = Union[dict[str, 'JSONData'], list['JSONData'], str, float, int, bool, None]

__all__ = [
    'JSONData', 'NodePin', 'NodeData', 'NodeParameter', 'NodeType', 'NodeProvider', 'ND', 'T',
    'ChoiceParameter', 'FloatParameter', 'generic_load_json'
]


@dataclass
class NodePin:
    pin_id: str
    multi_connect: bool
    io: Literal["in", "out", "in_out"]
    type: Any
    target_ids: list[tuple[str, str]] = field(default_factory=list)


class NodeData(ABC):
    id: str
    pins: dict[str, NodePin]

    @abstractmethod
    def to_json(self) -> JSONData:
        return generic_store_json(self)

    @property
    def inputs(self):
        return {n: p for n, p in self.pins.items() if "in" in p.io}

    @property
    def outputs(self):
        return {n: p for n, p in self.pins.items() if "out" in p.io}


T = TypeVar('T')


@dataclass
class NodeParameter(ABC, Generic[T]):
    name: str
    desc: str
    default: T

    @abstractmethod
    def check(self, value: T) -> bool:
        pass


@dataclass
class ChoiceParameter(NodeParameter[T]):
    choices: list[T]

    def check(self, value: T) -> bool:
        return value in self.choices


@dataclass
class FloatParameter(NodeParameter[float]):
    min: Optional[float]
    max: Optional[float]

    def check(self, value: float) -> bool:
        return (self.min is None or value < self.min) and (self.max is None or value < self.max)


ND = TypeVar('ND', bound=NodeData)


class NodeType(ABC, Generic[ND]):
    id: str
    name: str
    parameters: dict[str, NodeParameter]
    category: Optional[str] = None

    def create(self, node_id: str, arguments: dict[str, Any]) -> ND:
        raise NotImplementedError

    def _generic_create(self, node_id: str, callback: Callable[[str, ...], ND], arguments: dict[str, Any]):
        kwargs = {}
        for n, p in self.parameters.items():
            if n in arguments:
                assert p.check(arguments[n]), f"Invalid value for Parameter {n}: {arguments[n]!r}"
                kwargs[n] = arguments.pop(n)
            else:
                kwargs[n] = p.default
        assert not arguments, arguments
        print(kwargs)
        return callback(node_id, **kwargs)

    def load_json(self, data: JSONData) -> ND:
        raise NotImplementedError


class NodeProvider(ABC, Generic[ND]):
    @abstractmethod
    def node_types(self) -> list[NodeType[ND]]:
        raise NotImplementedError

    def is_compatible(self, start: tuple[ND, str], end: tuple[ND, str]) -> bool:
        sp = start[0].pins[start[1]]
        ep = end[0].pins[end[1]]
        return ("out" in sp.io and "in" in ep.io and sp.type == ep.type)

    def connect(self, start: tuple[ND, str], end: tuple[ND, str]):
        sp = start[0].pins[start[1]]
        ep = end[0].pins[end[1]]
        if not sp.multi_connect and len(sp.target_ids) > 0:
            raise ValueError(f"Can't connect another pin from start {start}")
        if not ep.multi_connect and len(ep.target_ids) > 0:
            raise ValueError(f"Can't connect another pin to end {end}")
        sp.target_ids.append((end[0].id, ep.pin_id))
        ep.target_ids.append((start[0].id, sp.pin_id))

    def disconnect(self, start: tuple[ND, str], end: tuple[ND, str]):
        sp = start[0].pins[start[1]]
        ep = end[0].pins[end[1]]
        sp.target_ids.remove((end[0].id, ep.pin_id))
        ep.target_ids.remove((start[0].id, sp.pin_id))


def generic_store_json(node_data: ND, **extra: Any) -> JSONData:
    def targets(pin_id, pin):
        assert pin_id == pin.pin_id, f"No matching pin_ids ({pin_id=} and {pin.pin_id=})"
        if not pin.multi_connect:
            assert len(pin.target_ids) <= 1, "Non multi-connect pin has multiple targets"
        for t in pin.target_ids:
            yield "|".join(t)

    return {
        "node_id": node_data.id,
        "pins":
            {
                pin_id: list(targets(pin_id, pin))
                for pin_id, pin in node_data.pins.items()
            },
        **extra
    }


def generic_load_json(json: JSONData, template: NodeData):
    template.id = json.pop("node_id")
    pins = json.pop("pins")
    for tpin_id, tpin in template.pins.items():
        targets = pins.pop(tpin_id, None)
        assert targets is not None, f"Missing data in json for pin {tpin_id} of {template.id}"
        tpin.target_ids = [t.split('|') for t in targets]
    assert not pins, f"Extra pin information in json (remaining {pins})"
    assert not json, f"Extra data in json has to be used before `generic_load_json` is called (remaining {json})"
