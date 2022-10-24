from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Events.EventLogger import EventLogger
    from Tasks.Task import Task

import importlib
from pkgutil import iter_modules
from inspect import isclass
import signal

import math
import atexit
from typing import Type

from GUIs import Colors
from Elements.LabelElement import LabelElement
import pygame

from Sources.EmptySource import EmptySource
from Sources.EmptyTouchScreenSource import EmptyTouchScreenSource
from Workstation.WorkstationGUI import WorkstationGUI

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sys
import os
import ast
from screeninfo import get_monitors


class Workstation:

    def __init__(self):
        self.tasks = {}
        self.event_loggers = {}

        # Core application details
        QCoreApplication.setOrganizationName("TNEL")
        QCoreApplication.setOrganizationDomain("tnelab.org")
        QCoreApplication.setApplicationName("Pybehav")

        # Load information from settings or set defaults
        settings = QSettings()
        # Store information on the available sources
        package_dir = "Sources/"
        for (_, module_name, _) in iter_modules([package_dir]):
            # import the module and iterate through its attributes
            module = importlib.import_module(f"Sources.{module_name}")
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if isclass(attribute):
                    # Add the class to this package's variables
                    globals()[attribute_name] = attribute
        if settings.contains("sources"):
            self.sources = eval(settings.value("sources"))
        else:
            self.sources = {"es": EmptySource(), "etss": EmptyTouchScreenSource("(1024, 768)")}
            settings.setValue("sources", '{"es": EmptySource(), "etss": EmptyTouchScreenSource("(1024, 768)")}')
        # Store the number of available chambers
        if settings.contains("n_chamber"):
            self.n_chamber = int(settings.value("n_chamber"))
        else:
            self.n_chamber = 1
            settings.setValue("n_chamber", self.n_chamber)

        # Store the position of the pygame window
        if settings.contains("pygame/offset"):
            offset = ast.literal_eval(settings.value("pygame/offset"))
        else:
            m = get_monitors()[0]
            offset = (m.width / 6, 30)
            settings.setValue("pygame/offset", str(offset))

        os.environ['SDL_VIDEO_WINDOW_POS'] = '%i,%i' % offset  # Position the pygame window
        pygame.init()
        pygame.display.set_caption("Pybehav")

        # Compute the arrangement of chambers in the pygame window
        if settings.contains("pygame/n_row"):
            self.n_row = int(settings.value("pygame/n_row"))
            self.n_col = int(settings.value("pygame/n_col"))
            self.w = int(settings.value("pygame/w"))
            self.h = int(settings.value("pygame/h"))
            self.task_gui = pygame.display.set_mode((self.w * self.n_col, self.h * self.n_row), pygame.RESIZABLE, 32)
        else:
            self.compute_chambergui()

        self.guis = {}
        app = QApplication(sys.argv)
        self.wsg = WorkstationGUI(self)
        self.thread_events = {}
        self.event_notifier = threading.Event()
        guithread = threading.Thread(target=lambda: self.gui_loop())
        guithread.start()
        taskthread = threading.Thread(target=lambda: self.loop())
        taskthread.start()
        eventthread = threading.Thread(target=lambda: self.event_loop())
        eventthread.start()
        self.stopping = False
        atexit.register(lambda: self.exit_handler())
        signal.signal(signal.SIGTERM, self.exit_handler)
        signal.signal(signal.SIGINT, self.exit_handler)
        sys.exit(app.exec())

    def compute_chambergui(self) -> None:
        settings = QSettings()
        szo = pygame.display.get_desktop_sizes()
        szo = szo[0]
        sz = (int(szo[0] * 5 / 6), int(szo[1] - 70))
        self.n_row = 1
        self.n_col = self.n_chamber
        self.w = math.floor(sz[0] / self.n_chamber)
        self.h = math.floor(sz[0] / self.n_chamber * 2)
        if self.h > sz[1]:
            self.h = sz[1]
            self.w = math.floor(sz[1] / 2)
        while self.h < math.floor(sz[1] / (self.n_row + 1)) or self.n_col * self.w > sz[0]:
            self.n_row += 1
            self.h = math.floor(sz[1] / self.n_row)
            self.w = math.floor(self.h / 2)
            self.n_col = math.ceil(self.n_chamber / self.n_row)
        settings.setValue("pygame/n_row", self.n_row)
        settings.setValue("pygame/n_col", self.n_col)
        settings.setValue("pygame/w", self.w)
        settings.setValue("pygame/h", self.h)
        settings.setValue("pyqt/w", int(szo[0] / 6))
        settings.setValue("pyqt/h", int(szo[1] - 70))
        self.task_gui = pygame.display.set_mode((self.w * self.n_col, self.h * self.n_row), pygame.RESIZABLE, 32)

    def add_task(self, chamber: int, task_name: str, address_file: str, protocol: str, task_event_loggers: list[EventLogger]) -> None:
        """
        Creates a Task and adds it to the chamber.

        Parameters
        ----------
        chamber : int
            The index of the chamber where the task will be added
        task_name : string
            The name corresponding to the Task class
        address_file : string
            The file path for the Address File
        protocol : string
            The file path for the Protocol
        task_event_loggers : list
            The list of EventLoggers for the task
        """
        # Import the selected Task
        task_module = importlib.import_module("Tasks." + task_name)
        task = getattr(task_module, task_name)
        metadata = {"chamber": chamber, "subject": "default"}
        self.tasks[chamber] = task(self, metadata, self.sources, address_file, protocol)  # Create the task
        self.event_loggers[chamber] = task_event_loggers
        self.thread_events[chamber] = (threading.Event(), threading.Event(), threading.Event(), threading.Event(),
                                       threading.Event(), threading.Event())
        for logger in task_event_loggers:
            logger.set_task(self.tasks[chamber])
        # Import the Task GUI
        gui = getattr(importlib.import_module("GUIs." + task_name + "GUI"), task_name + "GUI")
        # Position the GUI in pygame
        col = chamber % self.n_col
        row = math.floor(chamber / self.n_col)
        # Create the GUI
        self.guis[chamber] = gui(self.task_gui.subsurface(col * self.w, row * self.h, self.w, self.h),
                                 self.tasks[chamber])

    def switch_task(self, task_base: Task, task_name: Type[Task], protocol: str = None) -> Task:
        """
        Switch the active Task in a sequence.

        Parameters
        ----------
        task_base : Task
            The base Task of the sequence
        task_name : Class
            The next Task in the sequence
        protocol : dict
            Dictionary representing the protocol for the new Task
        """
        # Create the new Task as part of a sequence
        new_task = task_name(task_base, task_base.components, protocol)
        gui = getattr(importlib.import_module("GUIs." + task_name.__name__ + "GUI"), task_name.__name__ + "GUI")
        # Position the GUI in pygame
        col = task_base.metadata['chamber'] % self.n_col
        row = math.floor(task_base.metadata['chamber'] / self.n_col)
        # Create the GUI
        self.guis[task_base.metadata['chamber']].sub_gui = gui(
            self.task_gui.subsurface(col * self.w, row * self.h, self.w, self.h),
            new_task)
        return new_task

    def remove_task(self, chamber: int, del_loggers: bool = True) -> None:
        """
        Remove the Task from the specified chamber.

        Parameters
        ----------
        del_loggers
        chamber : int
            The chamber from which a Task should be removed
        """
        remove_thread = threading.Thread(target=lambda: self.remove_task_(chamber, del_loggers))
        remove_thread.start()

    def remove_task_(self, chamber: int, del_loggers: bool = True) -> None:
        self.thread_events[chamber][0].set()
        self.thread_events[chamber][1].wait()
        self.thread_events[chamber][2].wait()
        self.thread_events[chamber][4].wait()
        if del_loggers:
            for el in self.event_loggers[chamber]:  # Close all associated EventLoggers
                el.close_()
        for c in self.tasks[chamber].components:
            c.close()
        del self.tasks[chamber]
        del self.event_loggers[chamber]
        del self.guis[chamber]
        del self.thread_events[chamber]

    def start_task(self, chamber: int) -> None:
        """
        Start the Task in the specified chamber.

        Parameters
        ----------
        chamber : int
            The chamber corresponding to the Task that should be started
        """
        self.tasks[chamber].start__()  # Start the Task
        for el in self.event_loggers[chamber]:  # Start all EventLoggers and log initial events
            el.start_()
        self.thread_events[chamber][3].set()

    def stop_task(self, chamber: int) -> None:
        """
        Stop the Task in the specified chamber.

        Parameters
        ----------
        chamber : int
            The chamber corresponding to the Task that should be stopped
        """
        self.thread_events[chamber][3].clear()
        self.tasks[chamber].stop__()  # Stop the task

    def event_loop(self) -> None:
        while not self.stopping:
            self.event_notifier.wait()
            self.event_notifier.clear()
            event_keys = list(self.event_loggers.keys())
            for key in event_keys:
                if not self.thread_events[key][0].is_set():
                    ecopy = self.tasks[key].events.copy()
                    self.tasks[key].events = []
                    for el in self.event_loggers[key]:
                        if el.started:
                            el.log_events(ecopy)
                elif not self.thread_events[key][4].is_set():
                    self.thread_events[key][4].set()

    def loop(self) -> None:
        """
        Master event loop for all Tasks. Handles Task logic and Task Events.
        """

        while not self.stopping:
            st = time.perf_counter()
            events = pygame.event.get()  # Get mouse/keyboard events
            task_keys = list(self.tasks.keys())
            for key in task_keys:  # For each Task
                if not self.thread_events[key][0].is_set():
                    if len(self.tasks[key].events) > 0 and not self.event_notifier.is_set():
                        self.event_notifier.set()
                    if self.thread_events[key][3].is_set() and not self.tasks[key].paused:  # If the Task has been started and is not paused
                        self.tasks[key].main_loop__()  # Run the Task's logic loop
                        self.guis[key].handle_events(events)  # Handle mouse/keyboard events with the Task GUI
                        if self.tasks[key].is_complete():  # Stop the Task if it is complete
                            self.wsg.chambers[key].stop()
                elif not self.thread_events[key][2].is_set():
                    self.thread_events[key][2].set()
            print(time.perf_counter()-st)

    def gui_loop(self) -> None:
        last_frame = time.perf_counter()
        while not self.stopping:
            if time.perf_counter() - last_frame > 1/30:
                self.task_gui.fill(Colors.black)
                gui_keys = list(self.guis.keys())
                for key in gui_keys:  # For each Task
                    if not self.thread_events[key][0].is_set():
                        self.guis[key].draw()  # Update the GUI
                        # Draw GUI border and subject name
                        col = key % self.n_col
                        row = math.floor(key / self.n_col)
                        pygame.draw.rect(self.task_gui, Colors.white, pygame.Rect(col * self.w, row * self.h, self.w, self.h), 1)
                        LabelElement(self.guis[key], 10, self.h - 30, self.w, 20,
                                     self.tasks[key].metadata["subject"], SF=1).draw()
                    elif not self.thread_events[key][1].is_set():
                        self.thread_events[key][1].set()
                pygame.display.flip()  # Signal to pygame that the whole GUI has updated
                last_frame = time.perf_counter()

    def exit_handler(self, *args):
        """
        Callback for when py-behav is closed.
        """
        self.stopping = True
        for key in self.tasks:  # Stop all Tasks
            if self.tasks[key].started:
                self.stop_task(key)
            self.remove_task(key)
        for src in self.sources:  # Close all Sources
            self.sources[src].close_source()
