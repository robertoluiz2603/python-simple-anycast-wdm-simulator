import abc
from asyncio.windows_events import NULL
from email.charset import SHORTEST
from importlib.resources import path
from msilib.schema import Environment
from pickle import FALSE
import typing
from typing import Sequence
import numpy as np
from numpy import sort
if typing.TYPE_CHECKING:
    from core import Service
from typing import Tuple
from networkx import Graph
import routing_policies

class RestorationPolicy(abc.ABC):

    def __init__(self) -> None:
        self.env = None
        self.name = None

    #def HRP(self, services: Sequence['Service'], disaster_duration):
    @abc.abstractclassmethod
    def HRP(self, services: Sequence['Service'], disaster_duration):
        pass

    @abc.abstractclassmethod
    def shortestPath (self, service: 'Service') -> Tuple[bool, str, 'Path']:
        pass
    
    @abc.abstractclassmethod
    def sort_services (self, services: Sequence['Service']):
        pass

class HRPPolicy(RestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'OF'
   
    def is_path_viable(topology: 'Graph', path: 'Path', number_units: int) -> bool:
        for node in path.node_list:
            if topology.nodes[node]['failed']:
                return False
        for i in range(len(path.node_list) - 1):
            if topology[path.node_list[i]][path.node_list[i + 1]]['failed'] \
                or topology[path.node_list[i]][path.node_list[i + 1]]['available_units'] < number_units:
                return False
        return True

    def shortestPath (self, service: 'Service') -> Tuple[bool, str, 'Path']:
        closest_path = None
        dc = service.source
        closest_path_hops = np.finfo(0.0).max
        if self.env.topology.nodes[dc]['available_units'] >= service.computing_units:
            paths = self.env.topology.graph['ksp'][service.source, dc]
            for path in enumerate(paths):
                if routing_policies.is_path_viable(self.env.topology, path, service.network_units) and closest_path_hops > path.hops:
                    paths = self.env.topology.graph['ksp'][service.source, dc]
                    closest_path_hops = path.hops
                    closest_path = path
        return closest_path, closest_path_hops
    
    def restorePath( self, service: 'Service') ->None:
        service.failed = FALSE

        pass

    def relocateAndRestorePath(self, service:'Service', route: 'Service.route'):
        lowest_load = np.finfo(0.0).max  # initializes load to the maximum value of a float
        closest_dc = None
        closest_path = None
        for iddc, dc in enumerate(self.env.topology.graph['dcs']):
            if self.env.topology.nodes[dc]['available_units'] >= service.computing_units and self.env.topology.nodes[dc] != service.source:
                paths = self.env.topology.graph['ksp'][service.source, dc]
                for idp, path in enumerate(paths):
                    load = (routing_policies.get_max_usage(self.env.topology, path) / self.env.resource_units_per_link) * \
                           ((self.env.topology.nodes[dc]['total_units'] - self.env.topology.nodes[dc]['available_units']) /
                            self.env.topology.nodes[dc]['total_units'])
                    if HRPPolicy.is_path_viable(self.env.topology, path, service.network_units) and load < lowest_load:
                        lowest_load = load
                        closest_dc = dc
                        closest_path = path
        service.route = closest_path
        service.source = closest_dc
        return

    def dropService(self, service:'Service'):
        service.failed=True
        return      
    
    def sort_services (self, services: Sequence['Service']):
        
        temp: Sequence['Service']
        for i in range(len(services)):
            for j in range(0, len(services) - i - 1):
                if services[j].remaining_time > services[j + 1].remaining_time:
                    temp = services[j]
                    services[j] = services[j+1]
                    services[j+1] = temp
        return services

    def hop_count(self, path):
        pass

    def HRP(self, services: Sequence['Service'], disaster_duration):
        # TODO: implement the method
        restored_services = 0 
        failed_services = 0
        
        for service in services:
            service.remaining_time = (service.holding_time - disaster_duration)

        services = HRPPolicy.sort_services(self, services)
        '''
        if(services != None):
            print("remaining time: ")
            for service in services:
                print(service.remaining_time)
        else:
            return services
        '''
        for service in services:
            curRoute = selRoute = selDC = None
            if HRPPolicy.shortestPath(self, service) != None:
                selRoute = HRPPolicy.shortestPath(self, service)
                service.route = selRoute[0]
                service.failed = False
                restored_services+=1
            else:
                for dc_node in self.env.topology.graph['dcs']:
                    if (service.remaining_time > disaster_duration) and (self.env.topology.nodes[dc_node]['available_units'] > service.computing_units):
                        route = HRPPolicy.shortestPath(self, service)
                        curRoute = route

                        print("Current route: ", curRoute)
                        if curRoute[1] < selRoute[1]:
                            selRoute = curRoute
                if selRoute[0] != None:
                    HRPPolicy.relocateAndRestorePath(self, service, selRoute[0])
                    service.failed = False
                    restored_services+=1
                else:
                    HRPPolicy.dropService(self, service)
                    failed_services+=1

        return services
                               
        # 1. sort the services

        # 2. try to restore (find a path to it). if a path is available, set the route, provision, set to working

        #3. If not, try to find an available path from another DC

        #4 At last, if previous is not possible, drop the service