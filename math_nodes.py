import operator
from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from typing import Optional, Callable, Any

from nodes_interface import *
from nodes_interface import generic_load_json
from graphlib import TopologicalSorter


class MathNodeData(NodeData, ABC):
    @abstractmethod
    def calc(self, values: list[float]) -> list[float]:
        raise NotImplementedError

    @property
    def arguments(self) -> JSONData:
        return {
            name: getattr(self, name)
            for name in (getattr(self, "__parameters__", {}))
        }

    def to_json(self) -> JSONData:
        base = super(MathNodeData, self).to_json()
        base["arguments"] = self.arguments
        return base


@dataclass
class MathNodeType(NodeType):
    id: str
    name: str
    parameters: dict[str, NodeParameter]
    type: Callable[[Any, ...], MathNodeData]
    category: Optional[str] = 'math'

    def create(self, node_id: str, arguments: dict[str, Any]) -> ND:
        return super(MathNodeType, self)._generic_create(node_id, self.type, arguments)

    def load_json(self, data: JSONData) -> ND:
        arguments = data.pop("arguments")
        template = self.create("<TEMPLATE>", arguments)
        generic_load_json(data, template)
        return template


MATH_NODE_TYPES = {}


def _register(cls):
    MATH_NODE_TYPES[cls.__name__] = MathNodeType(
        cls.__name__,
        getattr(cls, '__display_name__', cls.__name__),
        getattr(cls, '__parameters__', {}),
        cls
    )
    return cls


@_register
@dataclass
class ConstantNode(MathNodeData):
    id: str
    value: float

    pins: list[NodePin] = field(default_factory=lambda: {"out": NodePin("out", True, "out", float)})

    def calc(self, values: list[float]) -> list[float]:
        return [self.value]

    __parameters__ = {
        "value": FloatParameter("Value", "", 1.0, None, None)
    }


@_register
@dataclass
class PrinterNode(MathNodeData):
    id: str
    pins: dict[str, NodePin] = field(default_factory=lambda: {"in": NodePin("in", True, "in", float)})

    def calc(self, values: list[float]) -> list[float]:
        print(*values)
        return []


@_register
@dataclass
class BinopNode(MathNodeData):
    id: str
    operator_name: str
    pins: dict[str, NodePin] = field(default_factory=lambda: {
        "a": NodePin("a", False, "in", float),
        "b": NodePin("b", False, "in", float),
        "out": NodePin("out", True, "out", float),
    })

    def calc(self, values: list[float]) -> list[float]:
        func = getattr(operator, self.operator_name)
        return [func(*values)]

    __parameters__ = {
        "operator_name": ChoiceParameter[str](
            "Operator Name",
            "",
            "add",
            ["add", "sub", "mul", "truediv"]
        )
    }


class MathNodeProvider(NodeProvider[MathNodeData]):
    def node_types(self) -> list[NodeType[MathNodeData]]:
        return list(MATH_NODE_TYPES.values())


class Calculator:
    def __init__(self):
        pass

    def evaluate(self, nodes: dict[str, MathNodeData]):
        sorter = TopologicalSorter()
        for name, node in nodes.items():
            sorter.add(name, *(tn for pn, p in node.inputs.items() for tn, tp in p.target_ids))
        sorter.prepare()
        values = {}
        while sorter.is_active():
            for name in sorter.get_ready():
                node = nodes[name]
                ins = [values[t] for pn, p in node.inputs.items() for t in p.target_ids]
                outs = node.calc(ins)
                for p, v in zip(node.outputs, outs):
                    values[(name, p)] = v
                sorter.done(name)


if __name__ == '__main__':
    from node_cmd import NodeCmd


    class MathCmd(NodeCmd):
        def do_evaluate(self, arg):
            calc = Calculator()
            calc.evaluate({s: nd for s, (nt, nd) in self.nodes.items()})

    DEFAULT = """
create v1 ConstantNode 5
create v2 ConstantNode 7
create a1 BinopNode add
create s1 BinopNode sub
create p1 PrinterNode

connect v1.out a1.a
connect v2.out a1.b
connect v1.out s1.a
connect v2.out s1.b

connect a1.out p1.in 
connect s1.out p1.in 
"""

    nc = MathCmd(MathNodeProvider())
    nc.cmdloop()
