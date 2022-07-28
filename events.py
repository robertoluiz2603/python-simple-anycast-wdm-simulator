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
    service.availability = service.service_time / service.holding_time
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

    if len(services_disrupted) > 0:
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
            service.relocated = False
        
        if len(env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['running_services']) != 0:
            env.logger.critical('Not all services were removed')
        
        # call the restoration strategy
        services_disrupted = env.restoration_policy.restore(services_disrupted)

        number_lost_services: int = 0
        number_restored_services: int = 0
        number_relocated_services: int =0
        
        for service in services_disrupted:
            if service.failed!=True:  # service could be restored
                number_restored_services += 1
            
                if service.relocated:
                    number_relocated_services+=1

            else:
                number_lost_services += 1

        # register statistics such as restorability
        if number_disrupted_services > 0:
            restorability = number_restored_services / number_disrupted_services
            env.logger.debug(f'Failure at {env.current_time}\tRestorability: {restorability}')
        # accummulating the totals in the environment object


        env.number_disrupted_services += number_disrupted_services
        env.number_restored_services += number_restored_services
        env.number_relocated_services += number_relocated_services
    
        # TODO: the code below is not thread safe and therefore might have strange formatting
        with open("results/"+env.output_folder+"/services_restoration.txt", "a") as txt:
            txt.write(f"\n\nTotal disrupted: \t\t\t{len(services_disrupted)}")
            txt.write(f"\nTotal restored (relocated): {number_restored_services} ({number_relocated_services})")
            txt.write(f"\nTotal lost: \t\t\t\t{number_lost_services}")

    env.add_event(Event(env.current_time + failure.duration, link_failure_departure, failure))

def link_failure_departure(env: 'Environment', failure: 'LinkFailure') -> None:
    # in this case, only a single link failure is at the network at a given point in time
    env.logger.debug(f'Failure repaired at time: {env.current_time}\tLink: {failure.link_to_fail}')

    # tracking departures
    env.tracked_results['link_failure_departures'].append(env.current_time)

    # put the link back in a working state
    env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['failed'] = False

    env.setup_next_link_failure()

def disaster_arrival(env: 'Environment', disaster: 'DisasterFailure') -> None:
    from core import Event

    env.tracked_results['link_disaster_arrivals'].append(env.current_time)
    env.logger.debug(f'Disaster arrived at time: {env.current_time}')

    services_disrupted: Sequence[Service] = []  # create an empty list

    #for node in disaster.nodes:
    #    env.topology.nodes[node]['failed'] = True
        # TODO: include services traversing this node into the list

    #Deve ser uma lista com todos os servicos falhos no desastre
    # get the list of disrupted services

    # extend the list with the running services
    for link_failure in disaster.links:
        env.logger.debug(f' - Link failed: {link_failure}')
        env.topology[link_failure[0]][link_failure[1]]['failed'] = True
        link_failed_services = []
        link_failed_services.extend(env.topology[link_failure[0]][link_failure[1]]['running_services'])
        for failed_service in link_failed_services:
            if failed_service not in services_disrupted:
                
                env.logger.debug(f'Releasing resources for service {failed_service}')
                env.release_path(failed_service)
                queue_size = len(env.events)
                env.remove_service_departure(failed_service)
                if queue_size -1 != len(env.events):
                    env.logger.critical('Event not removed!')
                # set it to a failed state
                failed_service.failed = True
                failed_service.relocated = False
                services_disrupted.append(failed_service)
        
        if len(env.topology[link_failure[0]][link_failure[1]]['running_services']) != 0:
            env.logger.critical('Not all services were removed')
    #A lista deve ser convertida em um conjunto
    number_disrupted_services = len(services_disrupted)
    
    # call the restoration strategy
    services_disrupted = env.restoration_policy.restore(services_disrupted)
 
    # post-process the services => compute stats
    number_lost_services: int = 0
    number_restored_services: int = 0
    number_relocated_services: int =0
    expected_capacity_loss: float = 0
    loss_cost: float = 0
    expected_loss_cost: float = 0
    for service in services_disrupted:
        expected_capacity_loss += service.expected_risk
        if service.failed!=True: 
             # service could be restored
            expected_loss_cost += service.expected_risk * service.expected_loss_cost
            number_restored_services += 1
            # puts the connection back into the network         
            
            if service.relocated:
                number_relocated_services+=1
        
        else:    
            # service could not be restored
            # computing the service time that can be later used to compute availability
            service.service_time = env.current_time - service.arrival_time
            # computing the availability <= 1.0
            service.availability = service.service_time / service.holding_time
            loss_cost += service.loss_cost    
            number_lost_services+=1        
    
    # register statistics such as restorability
    
    # accummulating the totals in the environment object
    if number_disrupted_services > 0:
        restorability = number_restored_services / number_disrupted_services
        env.logger.debug(f'Failure at {env.current_time}\tRestorability: {restorability}')
    
    env.number_disrupted_services += number_disrupted_services
    env.total_expected_capacity_loss += expected_capacity_loss
    env.total_loss_cost += loss_cost
    env.total_expected_loss_cost += expected_loss_cost
    env.number_restored_services += number_restored_services
    env.number_relocated_services += number_relocated_services 
    
    print("AECL: ")
    print(env.total_expected_capacity_loss)  
    
    # TODO: the code below is not thread safe and therefore might have strange formatting
    with open("results/"+env.output_folder+"/services_restoration.txt", "a") as txt:
        txt.write(f"\n\nTotal disrupted: \t\t\t{len(services_disrupted)}")
        txt.write(f"\nTotal restored (relocated): {number_restored_services} ({number_relocated_services})")
        txt.write(f"\nTotal lost: \t\t\t\t{number_lost_services}")
        txt.write(f"\nAECL: \t\t\t\t{env.total_expected_capacity_loss}")
               
    env.add_event(Event(env.current_time + disaster.duration, disaster_departure, disaster))
  

def disaster_departure(env: 'Environment', disaster: 'DisasterFailure') -> None:
    # in this case, only a single link failure is at the network at a given point in time
    env.logger.debug(f'Disaster repaired at time: {env.current_time} Links: {disaster.links}')

    # tracking departures
    env.tracked_results['link_disaster_departures'].append(env.current_time)

    # put the link back in a working state
    for link in disaster.links:
        env.topology[link[0]][link[1]]['failed'] = False

    for node in disaster.nodes:
        env.topology.nodes[node]['failed'] = False