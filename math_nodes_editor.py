from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from math_nodes import MathNodeProvider
from nodeeditor import NodeEditorApp, NodeRenderer
from nodes_interface import NodePin, NodeType, ND


class PinCircle(Widget):
    pass


class MathNodeRenderer(NodeRenderer):
    def render_node(self, node_type: NodeType[ND], node: ND) -> Widget:
        return Label(text=f"type: {node_type.name}\nid: {node.id}")

    def render_pin(self, pin: NodePin) -> Widget:
        return PinCircle(size=(10, 10))


Builder.load_file("math_nodes_editor.kv")
math_app = NodeEditorApp(MathNodeProvider(), MathNodeRenderer())
math_app.run()
