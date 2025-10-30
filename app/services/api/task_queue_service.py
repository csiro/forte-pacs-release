'''
Abstract API for all task queue services. A task queue service is responsible for mainting a queue of tasks to be executed asynchronously.
'''
from typing import  Callable, Any
from abc import ABC, abstractmethod


class TaskQueueService(ABC):
    '''
    Abstract base class for a task queue service.
    '''
    @abstractmethod
    async def init_service(self)->None:
        """ Abstract method to initialize the task queue service.
        """

    @abstractmethod
    async def enqueue_task(self, queue_name : str,function: Callable[[],None], *params: Any) -> Any:
        """
            Enqueue a task in the specified queue to be executed asynchronously.

            Args:
                queue_name (str): The name of the queue to enqueue the task in.
                function (Callable[[], None]): The function to be executed as the task.
                *params (Any): Any additional parameters to be passed to the function.

            Returns:
                Any: The result of the executed task.
        """
