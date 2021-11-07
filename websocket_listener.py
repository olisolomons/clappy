import asyncio
from typing import Callable, Optional, Awaitable
import threading
import websockets

import json


class WebSocketListener:
    def __init__(self, url: str, secret: str, actions: dict[str, Callable[[], None]]):
        self.secret = secret
        self.url = url
        self.actions = actions

        self.async_loop: Optional[asyncio.AbstractEventLoop] = None
        self.termination_notifier: Optional[asyncio.Lock] = None

    async def bump_the_server(self, ws):
        while True:
            await ws.send(json.dumps({'type': 'bump'}))
            await asyncio.sleep(2 * 60)

    async def websocket_listen(self, ws):
        await ws.send(json.dumps({'type': 'authenticate', 'secret': self.secret}))
        async for raw_msg in ws:
            msg = json.loads(raw_msg)

            if 'type' in msg and msg['type'] in self.actions:
                action = self.actions[msg['type']]
                action()

    def run_websocket_listen(self):
        self.async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.async_loop)

        self.termination_notifier = asyncio.Lock()

        async def run_websocket_listen_terminable():
            await self.termination_notifier.acquire()

            async with websockets.connect(self.url) as ws:
                listen_task = asyncio.create_task(self.websocket_listen(ws))
                bump_task = asyncio.create_task(self.bump_the_server(ws))

                await asyncio.wait([
                    asyncio.create_task(
                        asyncio.wait([
                            listen_task,
                            bump_task
                        ])
                    ),
                    asyncio.create_task(self.termination_notifier.acquire())
                ],
                    return_when=asyncio.FIRST_COMPLETED
                )

                listen_task.cancel()
                bump_task.cancel()

            await asyncio.sleep(0.1)
            print('\ndone')

        self.async_loop.run_until_complete(run_websocket_listen_terminable())
        self.async_loop.close()

    def listen(self, *, verbose=False):
        run_machine_thread = threading.Thread(target=self.run_websocket_listen)
        run_machine_thread.start()

        try:
            while True:
                inp = input("> ")
                if inp == "exit":
                    break
                else:
                    print(f'unknown command {inp}')
        except KeyboardInterrupt:
            pass

        async def terminate():
            self.termination_notifier.release()

        asyncio.run_coroutine_threadsafe(terminate(), self.async_loop)

        run_machine_thread.join()
