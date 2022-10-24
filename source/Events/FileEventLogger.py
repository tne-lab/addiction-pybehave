from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Events.Event import Event

from abc import ABCMeta, abstractmethod

from Events.EventLogger import EventLogger
import os


class FileEventLogger(EventLogger):
    __metaclass__ = ABCMeta
    """
    Abstract class defining the base requirements for an EventLogger that logs Event objects to a file on disk.

    Methods
    -------
    start()
        Opens the file
    close()
        Closes the file
    log_events(events)
        Handle saving of each Event in the input list to the file
    get_file_path()
        Returns the 
    """

    def __init__(self, output_folder: str = None):
        super().__init__()
        self.output_folder = output_folder
        self.log_file = None

    @abstractmethod
    def get_file_path(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def log_events(self, events: list[Event]) -> None:
        self.log_file.flush()

    def start(self) -> None:
        super(FileEventLogger, self).start()
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
        if self.log_file is not None:
            self.log_file.close()
        self.log_file = open(self.get_file_path(), "w")

    def close(self) -> None:
        if self.log_file is not None:
            self.log_file.close()
