from abc import ABC, abstractmethod
from typing import Generic, Any

import kivy
from kivy.graphics.transformation import Matrix
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, ListProperty
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.layout import Layout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scatter import ScatterPlane

kivy.require("2.0.0")
kivy.config.Config.set('input', 'mouse', 'mouse,disable_multitouch')

from kivy.app import App
from kivy.input.providers.mouse import MouseMotionEvent
from kivy.uix.behaviors import DragBehavior
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from nodes_interface import *


class NodeRenderer(ABC, Generic[ND]):
    @abstractmethod
    def render_node(self, node_type: NodeType[ND], node: ND) -> Widget:
        raise NotImplementedError

    @abstractmethod
    def render_pin(self, pin: NodePin) -> Widget:
        raise NotImplementedError


class NodeConnector(Widget):
    direction: float = NumericProperty(0)


class Connector:
    pin: Widget


class VisualNode(DragBehavior, RelativeLayout):
    renderer: NodeRenderer = ObjectProperty(None)
    inner: Widget = ObjectProperty(None, rebind=True)
    node_data: NodeData = ObjectProperty(None)
    node_type: NodeType = ObjectProperty(None)
    pins: list[Connector] = ListProperty()

    def render_pins(self):


class NodesContainer(ScatterPlane):
    renderer: NodeRenderer = ObjectProperty(None)
    provider: NodeProvider = ObjectProperty(None)
    nodes: dict[str, tuple[NodeType, NodeData, VisualNode]] = ObjectProperty(None)
    mouse_position: tuple[int, int] = ObjectProperty((0, 0))

    def __init__(self, **kwargs):
        super(NodesContainer, self).__init__(**kwargs)
        self.nodes = {}
        self._keyboard = Window.request_keyboard(
            None, self, 'text')
        Window.bind(mouse_pos=lambda w, p: setattr(self, 'mouse_position', self.to_local(*p)))
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

    def render_node(self, node_type: NodeType, node_data: NodeData):
        inner = self.renderer.render_node(node_type, node_data)
        vis = VisualNode()
        vis.inner = inner
        vis.add_widget(inner)
        inner.pos = 10, 10
        return vis

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if text in "0123456789":
            nt = self.provider.node_types()[(int(text) - 1) % len(self.provider.node_types())]
            self._create_node(nt, {}, self.mouse_position)

    def _create_node(self, nt: NodeType, arguments: dict[str, Any], pos: tuple[int, int]):
        if self.nodes:
            ni = str(max(map(int, self.nodes)) + 1)
        else:
            ni = 1
        nd = nt.create(ni, {})
        v = self.render_node(nt, nd)
        self.nodes[ni] = nt, nd, v
        self.add_widget(v)
        v.center = self.to_local(*pos)

    def on_touch_down(self, touch: MouseMotionEvent):
        if touch.button == "mouse5":
            if self.provider is None:
                print("Still None")
            else:
                nt = self.provider.node_types()[0]
                self._create_node(nt, {}, touch.pos)
            return True
        elif touch.is_mouse_scrolling:
            factor = None
            if touch.button == 'scrolldown':
                if self.scale < self.scale_max:
                    factor = 1.1
            elif touch.button == 'scrollup':
                if self.scale > self.scale_min:
                    factor = 1 / 1.1
            if factor is not None:
                self.apply_transform(Matrix().scale(factor, factor, factor),
                                     anchor=touch.pos)
        else:
            return super().on_touch_down(touch)


class NodeEditor(Widget):
    nodes_container: NodesContainer = ObjectProperty(None)
    renderer: NodeRenderer = ObjectProperty(None)
    provider: NodeProvider = ObjectProperty(None)


class FullNodeEditor(Widget):
    renderer: NodeRenderer = ObjectProperty(None)
    provider: NodeProvider = ObjectProperty(None)


class NodeEditorApp(App):
    def __init__(self, provider: NodeProvider, renderer: NodeRenderer):
        super(NodeEditorApp, self).__init__()
        self.provider = provider
        self.renderer = renderer

    def build(self):
        editor = FullNodeEditor()
        editor.provider = self.provider
        editor.renderer = self.renderer
        return editor
