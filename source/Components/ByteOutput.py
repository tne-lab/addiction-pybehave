from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Sources.Source import Source

from Components.Component import Component


class ByteOutput(Component):
    """
        Class defining a Toggle component in the operant chamber.

        Parameters
        ----------
        source : Source
            The Source related to this Component
        component_id : str
            The ID of this Component
        component_address : str
            The location of this Component for its Source

        Attributes
        ----------
        state : boolean
            Boolean indicating if the Component is currently toggled

        Methods
        -------
        get_state()
            Returns state
        toggle(on)
            Sets the Toggle state with the Source
        get_type()
            Returns Component.Type.DIGITAL_OUTPUT
    """

    def __init__(self, source: Source, component_id: str, component_address: str):
        self.state = 0
        super().__init__(source, component_id, component_address)

    def send(self, msg: int) -> None:
        self.source.write_component(self.id, msg)
        self.state = msg

    def get_state(self) -> int:
        return self.state

    @staticmethod
    def get_type() -> Component.Type:
        return Component.Type.DIGITAL_OUTPUT
