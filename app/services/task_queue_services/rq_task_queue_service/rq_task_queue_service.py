'''
    Implementation of task queue based on Redis Queue (https://python-rq.org)
'''
from typing import  Callable, Any
from redis import Redis
from rq import Queue
from app.services.api.task_queue_service import TaskQueueService

class RQTaskQueueService(TaskQueueService):
    '''
        Implementation of a Task queue based on RQ.
    '''
    def __init__(self,redis_url:str)-> None:
        """
            Initializes the RQTaskQueueService with the provided Redis URL.

            Args:
                redis_url (str): The URL of the Redis server to use for the task queue.
        """


        self.redis_url = redis_url



    async def init_service(self)->None:
        """
            NOP
        """

    async def enqueue_task(self, queue_name : str, function: Callable[[],None], *params: Any) -> Any:
        """
            Enqueue a task in the specified redis queue.

            Args:
                queue_name (str): The name of the queue to enqueue the task in.
                function (Callable[[], None]): The function to be executed as the task.
                *params (Any): Any additional parameters to be passed to the function.

            Returns:
                Any: The result of the executed task.
        """

        redis_conn = Redis.from_url(self.redis_url)
        temp=Queue(queue_name, connection=redis_conn)
        temp.enqueue(function,params)
