import abc
import typing
from typing import Sequence
if typing.TYPE_CHECKING:
    from core import Service

class RestorationPolicy(abc.ABC):

    def __init__(self) -> None:
        self.env = None
        self.name = None
    
    @abc.abstractclassmethod
    def restore(self, services: Sequence['Service']) -> None:
        pass
        


class OldestFirst(RestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'OF'
    
    def restore(self, services: Sequence['Service']) -> None:
        # TODO: implement the method

        # 1. sort the services

        # 2. try to restore (find a path to it)

        # if a path is available, set the route, provision, set to working

        for service in services:
            # here, we use the same routing policy as in the provisioning
            success, dc, path = self.env.routing_policy.route(service)
            if success:
                service.route = path
                service.failed = False
                self.env.provision_service(service)
            break  # TODO: remove this for a realistic scenario
