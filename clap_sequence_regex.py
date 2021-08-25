import asyncio
from typing import Callable, Optional, Awaitable
import threading
from clap_detector import ClapDetector
from constants import CHUNK
from settings import Settings, default_settings

from fsm import notifier, regular_expressions as rex
from fsm.deterministic_finite_state_machine import DFSMachine


class ClapSequenceRegex:
    def __init__(self,
                 generate_regex: Callable[[notifier.Notifier], Awaitable[rex.RegularExpression]],
                 settings: Settings = default_settings):
        self.clappy = ClapDetector(self.on_clap, settings=settings)

        self.generate_regex = generate_regex

        self.clap_notifier: Optional[notifier.Notifier] = None
        self.machine_loop: Optional[asyncio.AbstractEventLoop] = None
        self.termination_notifier: Optional[asyncio.Lock] = None

    def on_clap(self, clap_frame_number):
        fps = self.clappy.sample_rate / CHUNK
        clap_time = clap_frame_number / fps

        if self.clap_notifier is not None:
            asyncio.run_coroutine_threadsafe(self.clap_notifier.notify(), self.machine_loop)

    def run_machine(self):
        self.machine_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.machine_loop)

        self.clap_notifier = notifier.Notifier('clap')

        self.termination_notifier = asyncio.Lock()

        async def run_machine_terminable():
            await self.termination_notifier.acquire()

            regex = await self.generate_regex(self.clap_notifier)
            machine = DFSMachine.from_regular_expression(regex)

            run_machine_task = asyncio.create_task(machine.run())

            await asyncio.wait([
                run_machine_task,
                asyncio.create_task(self.termination_notifier.acquire())
            ],
                return_when=asyncio.FIRST_COMPLETED
            )

            run_machine_task.cancel()

            await asyncio.sleep(0.1)
            print('done')

        self.machine_loop.run_until_complete(run_machine_terminable())
        self.machine_loop.close()

    def listen(self, *, verbose=False):
        run_machine_thread = threading.Thread(target=self.run_machine)
        run_machine_thread.start()

        self.clappy.connect(verbose=verbose)
        self.clappy.listen(verbose=verbose)

        async def terminate():
            self.termination_notifier.release()

        asyncio.run_coroutine_threadsafe(terminate(), self.machine_loop)

        run_machine_thread.join()
