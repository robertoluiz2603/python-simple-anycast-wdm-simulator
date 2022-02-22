from os import link
from typing import Sequence
import typing


if typing.TYPE_CHECKING:  # avoid circular imports
    from core import Environment, Service, LinkFailure, DisasterFailure



def arrival(env: 'Environment', service: 'Service') -> None:
    # logging.debug('Processing arrival {} for policy {} load {} seed {}'
    #               .format(service.service_id, env.policy, env.load, env.seed))

    success, dc, path = env.routing_policy.route(service)

    if success:
        service.route = path
        env.provision_service(service)
    else:
        env.reject_service(service)

    env.setup_next_arrival()  # schedules next arrival


def departure(env: 'Environment', service: 'Service') -> None:
    # computing the service time that can be later used to compute availability
    service.service_time = env.current_time - service.arrival_time
    service.availability = 1.0  # leaving due to service time, so 100% availability
    env.release_path(service)


def link_failure_arrival(env: 'Environment', failure: 'LinkFailure') -> None:
    from core import Event

    # saving status
    env.tracked_results['link_failure_arrivals'].append(env.current_time)
    
    # put the link in a failed state
    env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['failed'] = True

    # get the list of disrupted services
    services_disrupted: Sequence[Service] = []  # create an empty list

    # extend the list with the running services
    services_disrupted.extend(env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['running_services'])
    number_disrupted_services: int = len(services_disrupted)

    env.logger.debug(f'Failure arrived at time: {env.current_time}\tLink: {failure.link_to_fail}\tfor {number_disrupted_services} services')

    for service in services_disrupted:
        # release all resources used
        env.logger.debug(f'Releasing resources for service {service}')
        env.release_path(service)

        queue_size = len(env.events)
        env.remove_service_departure(service)
        if queue_size -1 != len(env.events):
            env.logger.critical('Event not removed!')

        # set it to a failed state
        service.failed = True
    
    if len(env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['running_services']) != 0:
        env.logger.critical('Not all services were removed')
    
    # call the restoration strategy
    env.restoration_policy.restore(services_disrupted)

    # post-process the services => compute stats
    number_restored_services: int = 0
    for service in services_disrupted:
        if service.failed:  # service could not be restored
            # computing the service time that can be later used to compute availability
            service.service_time = env.current_time - service.arrival_time
            # computing the availability <= 1.0
            service.availability = service.service_time / service.holding_time
        
        else:  # service could be restored
            number_restored_services += 1
            # puts the connection back into the network
            
    # register statistics such as restorability
    if number_disrupted_services > 0:
        restorability = number_restored_services / number_disrupted_services
        env.logger.debug(f'Failure at {env.current_time}\tRestorability: {restorability}')
    # accummulating the totals in the environment object
    env.number_disrupted_services += number_disrupted_services
    env.number_restored_services += number_restored_services

    env.add_event(Event(env.current_time + failure.duration, link_failure_departure, failure))

def link_failure_departure(env: 'Environment', failure: 'LinkFailure') -> None:
    # in this case, only a single link failure is at the network at a given point in time
    env.logger.debug(f'Failure repaired at time: {env.current_time}\tLink: {failure.link_to_fail}')

    # tracking departures
    env.tracked_results['link_failure_departures'].append(env.current_time)

    # put the link back in a working state
    env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['failed'] = False

    env.setup_next_link_failure()
    

def links_disaster_arrival(env: 'Environment', disaster: 'DisasterFailure') -> None:
    from core import Event

    cs = open("results/check_services.txt", "a")
    total_services = 0
    total_restored = 0
    total_lost = 0

    env.tracked_results['link_disaster_arrivals'].append(env.current_time)
    env.logger.debug(f'Disaster arrived at time: {env.current_time}')
    count = 0
    link = []
    for link_failure in disaster.links:
        count +=1
        link = link_failure
        env.topology[link[0]][link[1]]['failed'] = True
        services_disrupted: Sequence[Service] = []  # create an empty list

        # extend the list with the running services
        services_disrupted.extend(env.topology[link[0]][link[1]]['running_services'])
        number_disrupted_services: int = len(services_disrupted)
        total_services += number_disrupted_services

        env.logger.debug(f'Disaster ({count}/2) Link: {link}\tfor {number_disrupted_services} services')

        for service in services_disrupted:
            # release all resources used
            env.logger.debug(f'Releasing resources for service {service}')
            env.release_path(service)

            queue_size = len(env.events)
            env.remove_service_departure(service)
            if queue_size -1 != len(env.events):
                env.logger.critical('Event not removed!')

            # set it to a failed state
            service.failed = True
        
        if len(env.topology[link[0]][link[1]]['running_services']) != 0:
            env.logger.critical('Not all services were removed')
        
        # call the restoration strategy
        env.restoration_policy.restore(services_disrupted)

        # post-process the services => compute stats
        number_restored_services: int = 0
        for service in services_disrupted:
            if service.failed:  # service could not be restored
                # computing the service time that can be later used to compute availability
                service.service_time = env.current_time - service.arrival_time
                # computing the availability <= 1.0
                service.availability = service.service_time / service.holding_time
            
            else:  # service could be restored
                number_restored_services += 1
                # puts the connection back into the network
        total_restored+=number_restored_services       
        # register statistics such as restorability
        if number_disrupted_services > 0:
            restorability = number_restored_services / number_disrupted_services
            env.logger.debug(f'Disaster ({count}/2) at {env.current_time}\tRestorability: {restorability}')

            total_lost += (number_disrupted_services-number_restored_services)

        # accummulating the totals in the environment object
        env.number_disrupted_services += number_disrupted_services
        env.number_restored_services += number_restored_services
    cs.write("\n\nTotal disrupted: \t")
    cs.write(str(total_services))
    cs.write("\nTotal restored: \t")
    cs.write(str(total_restored))
    cs.write("\nTotal lost: \t")
    cs.write(str(total_lost))
    cs.close()
    
    env.add_event(Event(env.current_time + disaster.duration, link_disaster_departure, disaster))
  

def link_disaster_departure(env: 'Environment', disaster: 'DisasterFailure') -> None:
    # in this case, only a single link failure is at the network at a given point in time
    env.logger.debug(f'Disaster repaired at time: {env.current_time} Links: {disaster.links}')

    # tracking departures
    env.tracked_results['link_disaster_departures'].append(env.current_time)

    # put the link back in a working state
    for link_failure in disaster.links:
        link = link_failure
        env.topology[link[0]][link[1]]['failed'] = False

    env.setup_next_link_disaster()