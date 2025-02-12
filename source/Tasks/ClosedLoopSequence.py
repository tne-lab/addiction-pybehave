from enum import Enum

from Tasks.TaskSequence import TaskSequence
from Tasks.Raw import Raw
from Tasks.ERP import ERP
from Tasks.ClosedLoop import ClosedLoop
from Tasks.PMA import PMA


class ClosedLoopSequence(TaskSequence):
    class States(Enum):
        PRE_RAW = 0
        PRE_ERP = 1
        CLOSED_LOOP = 2
        PMA = 4
        POST_ERP = 4
        POST_RAW = 5

    @staticmethod
    def get_tasks():
        return [Raw, ERP, ClosedLoop, PMA]

    # noinspection PyMethodMayBeStatic
    def get_constants(self):
        return {
            'pre_raw_protocol': None,
            'pre_erp_protocol': None,
            'closed_loop_protocol': None,
            'pma_protocol': None,
            'post_erp_protocol': None,
            'post_raw_protocol': None
        }

    def init_state(self):
        return self.States.PRE_RAW

    def init_sequence(self):
        return Raw, self.pre_raw_protocol

    def main_loop(self):
        if self.state == self.States.PRE_RAW and self.cur_task.is_complete():
            self.switch_task(ERP, self.States.PRE_ERP, self.pre_erp_protocol)
        elif self.state == self.States.PRE_ERP and self.cur_task.is_complete():
            self.switch_task(ClosedLoop, self.States.CLOSED_LOOP, self.closed_loop_protocol)
        elif self.state == self.States.CLOSED_LOOP and self.cur_task.is_complete():
            self.switch_task(PMA, self.States.PMA, self.pma_protocol)
        elif self.state == self.States.PMA and self.cur_task.is_complete():
            self.switch_task(ERP, self.States.POST_ERP, self.post_erp_protocol)
        elif self.state == self.States.POST_ERP and self.cur_task.is_complete():
            self.switch_task(Raw, self.States.POST_RAW, self.post_raw_protocol)

    def is_complete(self):
        return self.state == self.States.POST_RAW and self.cur_task.is_complete()
