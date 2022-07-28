import abc
import typing
from typing import Optional, Sequence
import numpy as np
if typing.TYPE_CHECKING:
    from core import Service
    from graph import Path
from typing import Tuple
from networkx import Graph

import routing_policies

class RestorationPolicy(abc.ABC):

    def __init__(self) -> None:
        self.env = None
        self.name = None

    @abc.abstractclassmethod
    def restore(self, services: Sequence['Service']):
        pass

    def drop_service(self, service: 'Service') -> None:
        """
        Drops a service due to not being possible to restore it.

        Args:
            service (Service): The service to be dropped.
        """
        service.service_time = self.env.current_time - service.arrival_time
        service.availability = service.service_time / service.holding_time


class DoNotRestorePolicy(RestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'DNR'
    
    def restore(self, services: Sequence['Service']):
        for service in services:
            self.drop_service(service)
        return services


class PathRestorationPolicy(RestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'PR'
    
    def restore_path(self, service: 'Service') -> bool:
        """
        Method that tries to restore a service to the same datacenter
        it is currently associated with.

        Args:
            service (Service): _description_

        Returns:
            bool: _description_
        """
        
        # tries to get a path
        path: Optional['Path'] = routing_policies.get_shortest_path(self.env.topology, service)

        # if a path was found, sets it and returns true
        if path is not None:
            service.route = path
            print ("Encontrou caminho")
            return True
        # if not, sets None and returns False
        else:
            service.route = None
            print("Nao encontrou caminho")
            return False

    def restore(self, services: Sequence['Service']):
        # TODO: implement the method
        restored_services = 0 
        relocated_services = 0
        failed_services = 0
        
        # docs: https://docs.python.org/3.9/howto/sorting.html#key-functions
        services = sorted(services, key=lambda x: x.holding_time - (self.env.current_time - x.arrival_time))
        '''
        if(services != None):
            print("remaining time: ")
            for service in services:
                print(service.remaining_time)
        else:
            return services
        '''
        for service in services:
            if self.restore_path(service):
                service.failed = False
                restored_services += 1
                self.env.provision_service(service)
                service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
            else:  # no alternative was found
                self.drop_service(service)
        return services


class PathRestorationWithRelocationPolicy(PathRestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'PRwR'

    def relocate_restore_path(self, service:'Service') -> bool:
        """
        Method that tries to find an alternative DC using the same routing
        policy as the one used for the routing of new arrivals.

        Args:
            service (Service): _description_

        Returns:
            _type_: _description_
        """
        success, dc, path = self.env.routing_policy.route(service)
        if success:
            service.route = path
            print("Realocou")
            return True
        else:
            service.route = None
            print("Nao realocou")
            return False

    def restore(self, services: Sequence['Service']):
        # TODO: implement the method
        restored_services = 0 
        relocated_services = 0
        failed_services = 0
        
        # remaining time = holding time - (current time - arrival time)
        # docs: https://docs.python.org/3.9/howto/sorting.html#key-functions
        services = sorted(services, key=lambda x: x.holding_time - (self.env.current_time - x.arrival_time))
        '''
        if(services != None):
            print("remaining time: ")
            for service in services:
                print(service.remaining_time)
        else:
            return services
        '''
        for service in services:
            print('trying', service)
            if self.restore_path(service):  # inherits this method from PathRestorationPolicy
                service.failed = False
                restored_services += 1
                self.env.provision_service(service)
                service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
            elif self.relocate_restore_path(service):
                service.failed = False
                service.relocated = True
                restored_services += 1
                relocated_services += 1
                self.env.provision_service(service)
                service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
            else:  # no alternative was found
                self.drop_service(service)
                failed_services+=1
            
        print("perdidos: ")
        print(failed_services)
        return services


class PathRestorationPropabilitiesAware(RestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'PRPA'
    
    def restore_path(self, service: 'Service') -> bool:
        """
        Method that tries to restore a service to the same datacenter
        it is currently associated with.

        Args:
            service (Service): _description_

        Returns:
            bool: _description_
        """
        
        # tries to get a path
        path: Optional['Path'] = routing_policies.get_safest_path(self.env.topology, service)

        # if a path was found, sets it and returns true
        if path is not None:
            service.route = path
            print ("Encontrou caminho")
            return True
        # if not, sets None and returns False
        else:
            service.route = None
            print("Nao encontrou caminho")
            return False
    def relocate_restore_path(self, service:'Service') -> bool:
        """
        Method that tries to find an alternative DC using the same routing
        policy as the one used for the routing of new arrivals.

        Args:
            service (Service): _description_

        Returns:
            _type_: _description_
        """
        success, dc, path = self.env.routing_policy.route(service)
        if success:
            service.route = path
            print("Realocou")
            return True
        else:
            service.route = None
            print("Nao realocou")
            return False
    def restore(self, services: Sequence['Service']):
        # TODO: implement the method
        restored_services = 0 
        relocated_services = 0
        failed_services = 0
        
        # docs: https://docs.python.org/3.9/howto/sorting.html#key-functions
        services = sorted(services, key=lambda x: x.holding_time - (self.env.current_time - x.arrival_time))
        '''
        if(services != None):
            print("remaining time: ")
            for service in services:
                print(service.remaining_time)
        else:
            return services
        '''
        for service in services:
            if self.restore_path(service):
                service.failed = False
                restored_services += 1
                self.env.provision_service(service)
                service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
            elif self.relocate_restore_path(service):
                service.failed = False
                service.relocated = True
                restored_services += 1
                relocated_services += 1
                self.env.provision_service(service)
                service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
            else:  # no alternative was found
                self.drop_service(service)
        return services