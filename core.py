from dis import dis
import logging
import random
import heapq
import multiprocessing
from typing import Any, Callable, List, Optional, Sequence
from dataclasses import dataclass, field
import numpy as np
from networkx import Graph
from graph import Path
import events
import plots
import routing_policies
import restoration_policies
import xml.etree.ElementTree as ET

class Environment:

    def __init__(self, args=None, topology=None, results=None, seed=None, load=None, 
                 routing_policy=None, id_simulation=None,
                 restoration_policy=None,
                 output_folder=None):

        if args is not None and hasattr(args, 'mean_service_holding_time'):
            self.mean_service_holding_time: float = args.mean_service_holding_time
        else:
            self.mean_service_holding_time: float = 86400.0  # service holding time in seconds (54000 sec = 15 h)

        self.iter_disaster = -1
        self.total_path_risk = 0.0
        self.total_hops_disrupted_services = 0.0
        self.total_hops_restaured_services = 0.0
        self.total_hops_relocated_services = 0.0
        self.load: float = 0.0
        self.cascade_affected_services = 0
        self.epicenter_happened = 0
        self.cascade_happened_73 = 0
        self.cascade_happened_15 = 0
        self.cascade_happened_0 = 0
        #self.priority_classes:float = [ 0.000003, 0.00000375]

        self.total_expected_loss_cost: float  = 0

        self.total_loss_cost: float = 0

        self.total_expected_capacity_loss: float = 0

        self.disaster_zones = ['Z1', 'Z2', 'Z3', 'Z4']
        #total number of disaster during a simulation
        self.number_disaster_occurences: int = len(self.disaster_zones) * 4
        self.number_disaster_processed: int = 0
        
        self.current_disaster_zone = []
        
        # total number of services disrupted by failures
        self.number_disrupted_services: int = 0
        # total number of services restored from failures
        self.number_restored_services: int = 0

        self.number_relocated_services: int =0
        # list with all services processed

        self.failed_again_services: int =0

        self.services: Sequence[Service] = []

        # TODO: implementar obtencao do valor a partir do args
        self.mean_failure_inter_arrival_time: float = 100000.
        self.mean_failure_duration: float = 86400.0

        self.mean_service_inter_arrival_time: float = 0.0
        if args is not None and hasattr(args, 'load') and load is None:
            self.set_load(load=args.load)
        elif load is not None:  # load through parameter has precedence over argument
            self.set_load(load=load)
        else:
            self.set_load(load=50)

        # num_seeds defines the number of seeds (simulations) to be run for each configuration
        self.num_seeds:int = 20
        if args is not None and hasattr(args, "num_seeds"):
            self.num_seeds = args.num_seeds

        # defines the number of DCs to be placed in the topology
        self.num_dcs: int = 4
        if args is not None and hasattr(args, "num_dcs"):
            self.num_dcs = args.num_dcs

        # defines the number of DCs to be placed in the topology
        self.dc_placement: str = 'degree'
        if args is not None and hasattr(args, "dc_placement"):
            self.dc_placement = args.dc_placement

        self.plot_simulation_progress: bool = False
        if args is not None and hasattr(args, "plot_simulation_progress"):
            self.plot_simulation_progress = args.plot_simulation_progress

        self.num_arrivals: int = 100000
        if args is not None and hasattr(args, "num_arrivals"):
            self.num_arrivals = args.num_arrivals

        self.k_paths: int = 5
        if args is not None and hasattr(args, "k_paths"):
            self.k_paths = args.k_paths

        self.threads: int = 7
        if args is not None and hasattr(args, 'threads'):
            self.threads = args.threads

        self.disaster_arrivals_interval:int = int(self.num_arrivals/ (self.number_disaster_occurences+1))
        self.next_disaster_point:int = int(self.disaster_arrivals_interval)

        self.topology_file: str = "nobel-us.xml"  #"nobel-us.xml" #"test-topo.xml"
        self.topology_name: str = 'nobel-us'
        # self.topology_file = "simple"  # "nobel-us.xml" #"test-topo.xml"
        # self.topology_name = 'simple'
        if args is not None and hasattr(args, 'topology_file'):
            self.topology_file = args.topology_file
            self.topology_name = args.topology_file.split('.')[0]    

        self.resource_units_per_link: int = 80
        if args is not None and hasattr(args, "resource_units_per_link"):
            self.resource_units_per_link = args.resource_units_per_link

        self.routing_policy: routing_policies.RoutingPolicy = routing_policies.ClosestAvailableDC()  # closest DC by default
        self.routing_policy.env = self
        if routing_policy is not None:
            self.routing_policy = routing_policy  # parameter has precedence over argument
            self.routing_policy.env = self
        
        self.restoration_policy: restoration_policies.RestorationPolicy = restoration_policies.DoNotRestorePolicy()
        self.restoration_policy.env = self
        if restoration_policy is not None:
            self.restoration_policy = restoration_policy
            self.restoration_policy.env = self

        self.topology: Graph = None
        if topology is not None:
            self.topology = topology

        self.seed: float = 42
        self.rng: random.Random = random.Random(42)
        if seed is not None:
            self.seed = seed
            self.rng = random.Random(seed)

        self.results: list = []  # initiates with an empty local results vector
        if results is not None:
            self.results = results

        self.id_simulation: int = 0
        if id_simulation is not None:
            self.id_simulation = id_simulation

        self.track_stats_every: int = 200  # frequency at which results are saved
        self.plot_tracked_stats_every: int = 2000  # frequency at which results are plotted
        self.tracked_results: dict = {}
        self.tracked_statistics: List[str] = ['request_blocking_ratio', 'average_link_usage', 'average_node_usage',
                                        'average_availability', 'average_restorability', 'link_failure_arrivals', 
                                        'link_failure_departures', 'link_disaster_arrivals', 'link_disaster_departures', 'average_relocation',
                                        'avg_expected_capacity_loss', 'avg_loss_cost', 'avg_expected_loss_cost',
                                        'avg_hops_disrupted_services', 'avg_hops_restaured_services', 'avg_hops_relocated_services',
                                        'avg_restaured_path_risk', 'cascade_affected_services', 'avg_services_affected',
                                        'avg_failed_before_services', 'epicenter_happened', 'cascade_happened_73', 'cascade_happened_15',
                                        'cascade_happened_5']
        for obs in self.tracked_statistics:
            self.tracked_results[obs] = []

        self.events: list = []  # event queue
        self._processed_arrivals: int = 0
        self._rejected_services: int = 0
        self.current_time: int = 0.0

        self.output_folder: str = 'data'
        if output_folder is not None:
            self.output_folder = output_folder
        elif args is not None and hasattr(args, "output_folder"):
            self.output_folder = args.output_folder

        self.plot_formats: tuple = ('pdf', 'svg')  # you can configure this to other formats such as PNG, SVG

        self.logger = logging.getLogger(f'env-{self.load}')  # TODO: colocar outras informacoes necessarias
        self.priority_class_list = self.priority_class_inicialization()

        

    def setup_disaster_zones(self):
        self.current_disaster_zone = []
        self.disaster_zones_list = []
        self.links = []
        tfpath = "config/topologies/"+self.topology_file
        elementTree = ET.parse(tfpath)
        root = elementTree.getroot()

        for zone in root.findall(".//zone"):
            regions_in_zone = []
            for region in root.findall(".//zone[@id='"+zone.attrib['id']+"']/region"):
                links = []
                for link in root.findall(".//zone[@id='"+zone.attrib['id']+"']/region[@id='"+region.attrib['id']+"']/disaster_link"):
                    link_tuple = []
                    for src in root.findall(".//link[@id='"+link.text+"']/source"):
                        link_src = src.text
                    for tgt in root.findall(".//link[@id='"+link.text+"']/target"):
                        link_tgt = tgt.text
                    
                    self.topology[link_src][link_tgt]['link_failure_probability'] = float(link.attrib['probability'])
                    link_tuple = []
                    link_tuple.append(link_src)
                    link_tuple.append(link_tgt)
                    link_tuple.append(float(link.attrib['probability']))
                    links.append(link_tuple)
                regions_in_zone.append(links)
            self.disaster_zones_list.append(regions_in_zone)  

        for idx, z in enumerate(self.disaster_zones_list):
            print("Zona: ", idx+1)
            for idx, r in enumerate(z):
                print("Regiao ", idx)
                print(r)
        return self.disaster_zones_list

    def priority_class_inicialization(self):
        priority_class_list = []
        pc1 = PriorityClass(priority=1,loss_cost=0.00000375,expected_loss_cost=0.0000075,max_degradation=0,max_delay=0)
        priority_class_list.append(pc1)
        '''
        pc2 = PriorityClass(priority=2,loss_cost=0.000003,expected_loss_cost=0.000006,max_degradation=0,max_delay=0)
        priority_class_list.append(pc2)
        
        pc3 = PriorityClass(priority=3,loss_cost=0.0000015,expected_loss_cost=0.000003,max_degradation=0,max_delay=0)
        priority_class_list.append(pc3)
        pc4 = PriorityClass(priority=4,loss_cost=0.0,expected_loss_cost=0.0,max_degradation=0,max_delay=0)
        priority_class_list.append(pc4)
        '''
        return priority_class_list

    def compute_simulation_stats(self):
        # run here the code to summarize statistics from this specific run
        if self.plot_simulation_progress:
            plots.plot_simulation_progress(self)
        
        total_service_time: float = 0.
        total_holding_time: float = 0.
        for service in self.services:
            if service.provisioned and service.service_time!=None:
                total_service_time += service.service_time
                total_holding_time += service.holding_time
        # add here the code to include other statistics you may want

        self.results[self.routing_policy.name][self.restoration_policy.name][self.load].append({
            'request_blocking_ratio': self.get_request_blocking_ratio(),
            'average_link_usage': np.mean([self.topology[n1][n2]['utilization'] for n1, n2 in self.topology.edges()]),
            'individual_link_usage': [self.topology[n1][n2]['utilization'] for n1, n2 in self.topology.edges()],
            'average_node_usage': np.mean([self.topology.nodes[node]['utilization'] for node in self.topology.graph['dcs']]),
            'individual_node_usage': {node: self.topology.nodes[node]['utilization'] for node in self.topology.graph['dcs']},
            'average_availability': total_service_time / total_holding_time,
            'average_restorability': self.number_restored_services / self.number_disrupted_services,
            'average_relocation': self.number_relocated_services / self.number_disrupted_services,
            'avg_loss_cost': self.total_loss_cost/self.number_disrupted_services,
            'avg_expected_loss_cost': self.total_expected_loss_cost/self.number_disrupted_services,
            'avg_expected_capacity_loss': self.total_expected_capacity_loss/self.number_disrupted_services,
            'avg_hops_disrupted_services': self.total_hops_disrupted_services/self.number_disrupted_services,
            'avg_hops_restaured_services': self.total_hops_restaured_services/self.number_restored_services,
            'avg_hops_relocated_services': self.total_hops_relocated_services/self.number_relocated_services,
            'cascade_affected_services': self.cascade_affected_services,
            'avg_services_affected': self.number_disrupted_services/self.number_disaster_occurences,
            'avg_failed_before_services': self.failed_again_services,
            'cascade_happened_73': self.cascade_happened_73,
            'cascade_happened_15': self.cascade_happened_15,
            'cascade_happened_5': self.cascade_happened_5,
            'epicenter_happened': self.epicenter_happened
        })
    def is_empty(self, list):
        empty = 1
        for item in list:
            if item != []:
                empty = 0
        return empty
        
    def random_class(self):
        '''
        #Selects a int from 1 to 18. Not in usage right now
        rand_class = random.randint(1, 18)
        priority_choose: PriorityClass()

        #According to the integer selected, it is defined the service's class
        if(rand_class<=2):
            priority_choose = self.priority_class_list[0]

        elif rand_class<=6 and rand_class>=3:
            priority_choose = self.priority_class_list[1]

        elif rand_class<=10 and rand_class>=7:
            priority_choose = self.priority_class_list[2]
            
        else:
            priority_choose = self.priority_class_list[3]

        '''
        priority_choose: PriorityClass()
       
        priority_choose = self.priority_class_list[0]

        #Returns the priority_class selected
        return priority_choose
        
    def reset(self, seed=None, id_simulation=None):
        self.iter_disaster = -1        
        self.epicenter_happened = 0
        self.cascade_happened_73 = 0
        self.cascade_happened_15 = 0
        self.cascade_happened_5 = 0
        self.setup_disaster_zones()
        self.events = []  # event queue
        self._processed_arrivals = 0
        self._rejected_services = 0
        self.current_time = 0.0
        self.total_hops_disrupted_services = 0.0
        self.total_hops_restaured_services = 0.0
        self.total_hops_relocated_services = 0.0
        self.cascade_affected_services = 0

        self.number_disaster_processed: int = 0
        self.total_expected_loss_cost: float  = 0

        self.total_loss_cost: float = 0

        self.total_expected_capacity_loss: float = 0

        # total number of services disrupted by failures
        self.number_disrupted_services: int = 0
        # total number of services restored from failures
        self.number_restored_services: int = 0

        self.number_relocated_services: int =0

        # list with all services processed
        self.services: Sequence[Service] = []

        for obs in self.tracked_statistics:
            self.tracked_results[obs] = []

        if seed is not None:
            self.seed = seed
            self.rng = random.Random(seed)
        if id_simulation is not None:
            self.id_simulation = id_simulation

        self.next_disaster_point = self.disaster_arrivals_interval

        self.disaster_zones = ['Z1', 'Z2', 'Z3', 'Z4']

        # (re)-initialize the graph
        self.topology.graph['running_services'] = []
        for idx, lnk in enumerate(self.topology.edges()):
            self.topology[lnk[0]][lnk[1]]['available_units'] = self.resource_units_per_link
            self.topology[lnk[0]][lnk[1]]['total_units'] = self.resource_units_per_link
            self.topology[lnk[0]][lnk[1]]['services'] = []
            self.topology[lnk[0]][lnk[1]]['running_services'] = []
            self.topology[lnk[0]][lnk[1]]['id'] = idx
            self.topology[lnk[0]][lnk[1]]['utilization'] = 0.0
            self.topology[lnk[0]][lnk[1]]['last_update'] = 0.0
            self.topology[lnk[0]][lnk[1]]['link_failure_probability'] = 0
        for idx, node in enumerate(self.topology.nodes()):
            if self.topology.nodes[node]['dc']:
                #self.topology.nodes[node]['available_units'] = self.topology.degree(node) * self.resource_units_per_link
                #self.topology.nodes[node]['total_units'] = self.topology.degree(node) * self.resource_units_per_link
                self.topology.nodes[node]['available_units'] = 1800
                self.topology.nodes[node]['total_units'] = 1800
                #self.topology.nodes[node]['available_units'] = 700
                #self.topology.nodes[node]['total_units'] = 700
                self.topology.nodes[node]['services'] = []
                self.topology.nodes[node]['running_services'] = []
                self.topology.nodes[node]['id'] = idx
                self.topology.nodes[node]['utilization'] = 0.0
                self.topology.nodes[node]['last_update'] = 0.0
                self.topology.nodes[node]['total_storage'] = 0
                self.topology.nodes[node]['available_storage'] = 0
                self.topology.nodes[node]['node_failure_probability'] =0
            else:
                self.topology.nodes[node]['node_failure_probability'] =0
                self.topology.nodes[node]['available_units'] = 0
                self.topology.nodes[node]['total_units'] = 0        

        self.setup_next_arrival()


    def setup_next_arrival(self):
        """
        Returns the next arrival to be scheduled in the simulator
        """
        if self._processed_arrivals > self.num_arrivals:
            return  # returns None when all arrivals have been processed
        at = self.current_time + self.rng.expovariate(1 / self.mean_service_inter_arrival_time)

        ht = self.rng.expovariate(1 / self.mean_service_holding_time)
        src = self.rng.choice([x for x in self.topology.graph['source_nodes']])
        src_id = self.topology.graph['node_indices'].index(src)

        #Randomly picks a class for the service
        #TODO: use self.rng
        pc:PriorityClass()= self.random_class()

        self._processed_arrivals += 1

        if self._processed_arrivals % self.track_stats_every == 0:
            self.tracked_results['request_blocking_ratio'].append(self.get_request_blocking_ratio())
            self.tracked_results['average_link_usage']\
                .append(np.mean([
                    (self.topology[n1][n2]['total_units'] - self.topology[n1][n2]['available_units'])
                    / self.topology[n1][n2]['total_units'] for n1, n2 in self.topology.edges()
                ]))
            self.tracked_results['average_node_usage'].append(np.mean([(self.topology.nodes[node]['total_units'] -
                                                                        self.topology.nodes[node]['available_units']) /
                                                                       self.topology.nodes[node]['total_units'] for node
                                                                       in self.topology.graph['dcs']]))
            # failure-related stats
            total_service_time: float = 0.
            total_holding_time: float = 0.
            for service in self.services:
                if service.provisioned and service.service_time is not None:  # only the services which already left the system, i.e., have a service time
                    total_service_time += service.service_time
                    total_holding_time += service.holding_time
            if total_holding_time!=0:
                self.tracked_results['average_availability'].append(total_service_time / total_holding_time)
            if self.number_disrupted_services > 0:  # avoid division by zero
                self.tracked_results['average_restorability'].append(self.number_restored_services / self.number_disrupted_services)
                self.tracked_results['average_relocation'].append(self.number_relocated_services / self.number_disrupted_services)
                self.tracked_results['avg_expected_capacity_loss'].append(self.total_expected_capacity_loss / self.number_disrupted_services)
                self.tracked_results['avg_expected_loss_cost'].append(self.total_expected_loss_cost/self.number_disrupted_services)
                self.tracked_results['avg_loss_cost'].append(self.total_loss_cost/self.number_disrupted_services)
                self.tracked_results['avg_hops_disrupted_services'].append(self.total_hops_disrupted_services/self.number_disrupted_services)
                self.tracked_results['cascade_affected_services'].append(self.cascade_affected_services)
                self.tracked_results['avg_services_affected'].append(self.number_disrupted_services/self.number_disaster_occurences)
                self.tracked_results[ 'avg_failed_before_services'].append(self.failed_again_services)
                if self.number_restored_services >0:
                    self.tracked_results['avg_hops_restaured_services'].append(self.total_hops_restaured_services/self.number_restored_services)
                if self.number_relocated_services > 0:
                    self.tracked_results['avg_hops_relocated_services'].append(self.total_hops_relocated_services/self.number_relocated_services)
            else:  # if no failures, 100% restorability
                self.tracked_results['avg_loss_cost'].append(0.0)
                self.tracked_results['average_restorability'].append(1.)
                self.tracked_results['average_relocation'].append(0.0)
                self.tracked_results['avg_expected_capacity_loss'].append(0.0)
                self.tracked_results['avg_expected_loss_cost'].append(0.0)
                self.tracked_results['cascade_affected_services'].append(0.0)
                self.tracked_results['avg_services_affected'].append(0.0)
                self.tracked_results['avg_failed_before_services'].append(0)
            self.tracked_results['epicenter_happened'].append(self.epicenter_happened)
            self.tracked_results['cascade_happened_73'].append(self.cascade_happened_73)
            self.tracked_results['cascade_happened_15'].append(self.cascade_happened_15)
            self.tracked_results['cascade_happened_5'].append(self.cascade_happened_5)

        if self._processed_arrivals % self.plot_tracked_stats_every == 0:
            plots.plot_simulation_progress(self)
        
        next_arrival = Service(service_id=self._processed_arrivals, 
                               arrival_time=at, 
                               holding_time=ht,
                               source=src, 
                               source_id=src_id,
                               computing_units=random.randint(1, 5), #TODO: use self.rng
                               priority_class=pc)
        if((self._processed_arrivals == self.next_disaster_point) and self.number_disaster_processed<self.number_disaster_occurences):
            if(self.is_empty(self.current_disaster_zone)):
                if(self.iter_disaster<3):
                    self.iter_disaster+=1
                self.current_disaster_zone = self.disaster_zones_list[self.iter_disaster]
                
            
            self.setup_next_disaster()
            self.number_disaster_processed+=1
            self.next_disaster_point += self.disaster_arrivals_interval

        self.services.append(next_arrival)
        self.add_event(Event(next_arrival.arrival_time, events.arrival, next_arrival))

    def set_load(self, load=None, mean_service_holding_time=None):
        if load is not None:
            self.load = load
        if mean_service_holding_time is not None:  # service holding time in seconds (10800 sec = 3 h)
            self.mean_service_holding_time = mean_service_holding_time
        self.mean_service_inter_arrival_time = 1 / float(self.load / float(self.mean_service_holding_time))

    def add_event(self, event):
        """
        Adds an event to the event list of the simulator.
        This implementation is based on the functionalities of heapq: https://docs.python.org/2/library/heapq.html
        :param event:
        :return: None
        """
        # self.debug("time={}; event={}".format(event.time, event.call))
        heapq.heappush(self.events, (event.time, event))
    
    def remove_service_departure(self, service) -> None:
        for event in self.events:
            if event[1].params == service:
                self.events.remove(event)
                break

    def provision_service(self, service):
        service.destination = service.route.node_list[-1]
        service.destination_id = self.topology.graph['node_indices'].index(service.destination)

        # provisioning service at the DC
        self.topology.nodes[service.destination]['available_units'] -= service.computing_units
        self.topology.nodes[service.destination]['services'].append(service)
        self.topology.nodes[service.destination]['running_services'].append(service)
        self._update_node_stats(service.destination)

        # provisioning the path
        for i in range(len(service.route.node_list) - 1):
            self.topology[service.route.node_list[i]][service.route.node_list[i + 1]]['available_units'] -= service.network_units
            self.topology[service.route.node_list[i]][service.route.node_list[i + 1]]['services'].append(service)
            self.topology[service.route.node_list[i]][service.route.node_list[i + 1]]['running_services'].append(service)
            self._update_link_stats(service.route.node_list[i], service.route.node_list[i + 1])
        service.provisioned = True

        self.topology.graph['running_services'].append(service)
        self._update_network_stats()

        # schedule departure
        self.add_event(Event(service.arrival_time + service.holding_time, events.departure, service))

    def reject_service(self, service):
        service.provisioned = False
        self._rejected_services += 1

    def release_path(self, service):
        # provisioning service at the DC
        self.topology.nodes[service.destination]['available_units'] += service.computing_units
        self.topology.nodes[service.destination]['running_services'].remove(service)
        self._update_node_stats(service.destination)
        for i in range(len(service.route.node_list) - 1):
            self.topology[service.route.node_list[i]][service.route.node_list[i + 1]]['available_units'] += service.network_units
            self.topology[service.route.node_list[i]][service.route.node_list[i + 1]]['running_services'].remove(service)
            self._update_link_stats(service.route.node_list[i], service.route.node_list[i + 1])
        self._update_network_stats()

    def setup_next_link_failure(self):
        """
        Returns the next arrival to be scheduled in the simulator
        """
        if self._processed_arrivals > self.num_arrivals:
            return  # returns None when all arrivals have been processed
        
        # TODO: qual distribuicao sera usada pras falhas?
        at = self.current_time + self.rng.expovariate(1 / self.mean_failure_inter_arrival_time)
        duration = self.rng.expovariate(1 / self.mean_failure_duration)

        link = self.rng.choice([x for x in self.topology.edges()])

        failure = LinkFailure(link, at, duration)

        self.add_event(Event(failure.arrival_time, events.link_failure_arrival, failure))

   
    def setup_next_disaster(self):
        self.cascade_affected_services = 0
        if self._processed_arrivals > self.num_arrivals:
            return
            
        region_to_fail = []
        nodes_to_fail=[]
        if(self.current_disaster_zone[0]!=[]):
            region_to_fail = self.current_disaster_zone[0]
            self.current_disaster_zone[0] = []
            self.epicenter_happened = 1
        else:
            reg_prob = self.rng.randint(1,100)
            if reg_prob<73 and self.current_disaster_zone[1]!=[]:
                region_to_fail = self.current_disaster_zone[1]
                self.current_disaster_zone[1] = []
                self.cascade_happened_73 = 1
            elif reg_prob < 15 and self.current_disaster_zone[2]!=[]:
                region_to_fail = self.current_disaster_zone[2]
                self.current_disaster_zone[2] = []
                self.cascade_happened_15 = 1
            elif reg_prob < 5 and self.current_disaster_zone[3]!=[]:
                region_to_fail = self.current_disaster_zone[3]
                self.current_disaster_zone[3] = []
                self.cascade_happened_5 = 1

            else:
                region_to_fail = []
                self.cascade_happened_73 = 0
                self.cascade_happened_15 = 0
                self.cascade_happened_5 = 0
                if (self.current_disaster_zone[0] == []):
                    self.current_disaster_zone[1] = []
                if (self.current_disaster_zone[1] == []):
                    self.current_disaster_zone[2] = []
                if (self.current_disaster_zone[2] == []):
                    self.current_disaster_zone[3] = []
                return
            
                
            
        links_to_fail = []

        for link in region_to_fail:
            link_src_tgt = []
            for idx, item in enumerate(link):
                if idx<2:
                    link_src_tgt.append(item)
                else:
                    self.topology[link_src_tgt[0]][link_src_tgt[1]]['link_failure_probability'] = float(item)    
            links_to_fail.append(link_src_tgt)

        at = self.current_time + self.rng.expovariate(1/self.mean_failure_inter_arrival_time)
        duration = self.rng.expovariate(1/self.mean_failure_duration)
        
        disaster = DisasterFailure(links_to_fail, nodes_to_fail, at, duration)
        self.add_event(Event(disaster.arrival_time, events.disaster_arrival, disaster))

    def _update_link_stats(self, node1, node2):
        """
        Updates link statistics following a time-weighted manner.
        """
        last_update = self.topology[node1][node2]['last_update']
        time_diff = self.current_time - self.topology[node1][node2]['last_update']
        if self.current_time > 0:
            last_util = self.topology[node1][node2]['utilization']
            cur_util = (self.resource_units_per_link - self.topology[node1][node2]['available_units']) / self.resource_units_per_link
            # utilization is weighted by the time
            utilization = ((last_util * last_update) + (cur_util * time_diff)) / self.current_time
            self.topology[node1][node2]['utilization'] = utilization
        self.topology[node1][node2]['last_update'] = self.current_time

    def _update_node_stats(self, node):
        """
        Updates node statistics following a time-weighted manner.
        """
        last_update = self.topology.nodes[node]['last_update']
        time_diff = self.current_time - self.topology.nodes[node]['last_update']
        if self.current_time > 0:
            last_util = self.topology.nodes[node]['utilization']
            cur_util = (self.topology.nodes[node]['total_units'] - self.topology.nodes[node]['available_units']) / self.topology.nodes[node]['total_units']
            # utilization is weighted by the time
            utilization = ((last_util * last_update) + (cur_util * time_diff)) / self.current_time
            self.topology.nodes[node]['utilization'] = utilization
        self.topology.nodes[node]['last_update'] = self.current_time

    def _update_network_stats(self):
        """
        Updates statistics related to the entire network. To be implemented using the particular stats necessary for your problem.
        """
        pass

    def get_request_blocking_ratio(self):
        return float(self._rejected_services) / float(self._processed_arrivals)


def run_simulation(env: Environment):
    """
    Launches the simulation for one particular configuration represented by the env object.
    """
    logger = multiprocessing.log_to_stderr()
    logger.setLevel(logging.INFO)
    logger.info(f'Running simulation for load {env.load} and policy {env.routing_policy.name}')

    for seed in range(env.num_seeds):
        env.reset(seed=env.seed + seed, id_simulation=seed)  # adds to the general seed
        logger.info(f'Running simulation {seed} for policy {env.routing_policy.name} and load {env.load}')
        while len(env.events) > 0:
            event_tuple = heapq.heappop(env.events)
            time = event_tuple[0]
            env.current_time = time
            event = event_tuple[1]
            event.call(env, event.params)

        env.compute_simulation_stats()
    # prepare observations
    logger.info(f'Finishing simulation for load {env.load} and policy {env.routing_policy.name}')

@dataclass
class PriorityClass:
    priority: int = 0
    loss_cost: float = 0.0
    expected_loss_cost: float = 0.0
    max_degradation: float = 0.0
    max_delay: float = 0.0

@dataclass(eq=False, repr=False)
class Service:
    """"
    Class that defines one service in the system.
    """
    service_id: int = field(compare=True)
    arrival_time: float
    holding_time: float
    source: str
    source_id: int
    priority_class: PriorityClass #It is the priority and the rules used to restore this service
    expected_risk: float = 0.0
    destination: Optional[str] = field(init=False)
    destination_id: Optional[int] = field(init=False)
    route: Optional[Path] = field(init=False)
    service_time: Optional[float] = field(init=False, default=None)
    availability: Optional[float] = field(init=False)
    network_units: int = field(default=1)
    computing_units: int = field(default=1)
    provisioned: bool = field(default=False)
    failed: bool = field(default=False)
    failed_before: bool = field(default=False)
    relocated: bool = field(default=False)
    
    def __repr__(self) -> str:
        return f'<Service {self.service_id}, {self.source} -> {self.destination}>'
    
    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, Service):
            return self.service_id == other.service_id
        return False

@dataclass
class LinkFailure:
    link_to_fail: Sequence[str]
    arrival_time: float
    duration: float

@dataclass
class DisasterFailure:
    links: Sequence[Sequence[str]]
    nodes: Sequence[str]
    arrival_time: float
    duration: float

@dataclass
class Event:
    """
    Class that models one event of the event queue.
    """
    time: float
    call: Callable
    params: Any
