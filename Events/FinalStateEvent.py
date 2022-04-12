from Events.Event import Event


class FinalStateEvent(Event):
    def __init__(self, final_state, entry_time, metadata=None):
        super().__init__(entry_time, metadata)
        self.final_state = final_state
