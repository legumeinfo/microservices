import json
import uuid
from aio_pika import connect, Message
from functools import partial


class RPC(object):

  def __init__(self, loop):
    self.connection = None
    self.channel = None
    self.callback_queue = None
    self.futures = {}
    self.loop = loop

  async def connect(self):
    self.connection = await connect(
      "amqp://guest:guest@localhost/",
      loop=self.loop
    )
    self.channel = await self.connection.channel()
    self.callback_queue = await self.channel.declare_queue(
      exclusive=True
    )
    await self.callback_queue.consume(self.on_response)
    return self

  async def close(self):
    await self.channel.close()
    await self.connection.close()

  async def on_message(self, handler, exchange, message):
    with message.process():
      params = json.loads(message.body.decode())
      response = json.dumps(await handler(params))
      await exchange.publish(
        Message(
          body=response.encode(),
          correlation_id=message.correlation_id
        ),
        routing_key=message.reply_to
      )

  async def consume_queue(self, name, handler):
    queue = await self.channel.declare_queue(name)
    await queue.consume(
      partial(
        partial(self.on_message, handler),
        self.channel.default_exchange
      )
    )

  def on_response(self, message):
    future = self.futures.pop(message.correlation_id)
    future.set_result(message.body)

  async def call(self, queue, params):
    correlation_id = str(uuid.uuid4()).encode()
    future = self.loop.create_future()
    self.futures[correlation_id] = future
    await self.channel.default_exchange.publish(
      Message(
        json.dumps(params).encode(),
        content_type='text/plain',
        correlation_id=correlation_id,
        reply_to=self.callback_queue.name,
      ),
      routing_key=queue,
    )
    return json.loads(await future)
