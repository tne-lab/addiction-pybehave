from enum import Enum
from Components.NosePoke import NosePoke
from Events.InputEvent import InputEvent
from Tasks.Task import Task


class DPALHabituation2(Task):
    class States(Enum):
        INPUT = 0
        INTER_TRIAL_INTERVAL = 1

    class Inputs(Enum):
        INIT_ENTERED = 0
        INIT_EXIT = 1

    def __init__(self, chamber, source, address_file, protocol):
        super().__init__(chamber, source, address_file, protocol)
        self.fan.toggle(True)

    def start(self):
        self.state = self.States.INPUT
        self.init_light.toggle(True)
        super(DPALHabituation2, self).start()

    def main_loop(self):
        super().main_loop()
        self.events = []
        init_poke = self.init_poke.check()
        if init_poke == NosePoke.POKE_ENTERED:
            self.events.append(InputEvent(self.Inputs.INIT_ENTERED, self.cur_time - self.start_time))
        elif init_poke == NosePoke.POKE_EXIT:
            self.events.append(InputEvent(self.Inputs.INIT_EXIT, self.cur_time - self.start_time))
        if self.state == self.States.INPUT:
            if init_poke == NosePoke.POKE_ENTERED:
                self.init_light.toggle(False)
                self.food.dispense()
                self.tone.play_sound(1800, 1, 1)
                self.change_state(self.States.INTER_TRIAL_INTERVAL)
        elif self.state == self.States.INTER_TRIAL_INTERVAL:
            if self.cur_time - self.entry_time > self.inter_trial_interval:
                self.init_light.toggle(True)
                self.change_state(self.States.INPUT)

    def get_variables(self):
        return {
            'duration': 20,
            'inter_trial_interval': 10
        }

    def is_complete(self):
        return self.cur_time - self.start_time > self.duration * 60
