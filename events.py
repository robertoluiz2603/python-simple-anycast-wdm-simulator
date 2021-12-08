import copy
from typing import Sequence
import typing
if typing.TYPE_CHECKING:  # avoid circular imports
    from core import Environment, Service, LinkFailure


def arrival(env: 'Environment', service: 'Service'):
    # logging.debug('Processing arrival {} for policy {} load {} seed {}'
    #               .format(service.service_id, env.policy, env.load, env.seed))

    success, dc, path = env.routing_policy.route(service)

    if success:
        service.route = path
        env.provision_service(service)
    else:
        env.reject_service(service)

    env.setup_next_arrival()  # schedules next arrival


def departure(env: 'Environment', service: 'Service'):
    env.release_path(service)


#link como parametro
def link_failure_arrival(env: 'Environment', failure: 'LinkFailure'):
    from core import Event
    
    # put the link in a failed state
    env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['failed'] = True

    # get the list of disrupted services
    services_disrupted: Sequence[Service] = copy.deepcopy(env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['running_services'])
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
            pass
        
        else:  # service could be restored
            number_restored_services += 1
            # puts the connection back into the network
            
    # register statistics such as restorability
    if number_disrupted_services > 0:
        restorability = number_restored_services / number_disrupted_services

    # verificar servicoes rompidos por esta falha
    env.add_event(Event(env.current_time + failure.duration, link_failure_departure, failure))


def link_failure_departure(env: 'Environment', failure: 'LinkFailure'):
    # in this case, only a single link failure is at the network at a given point in time
    env.logger.debug(f'Failure repaired at time: {env.current_time}\tLink: {failure.link_to_fail}')

    # put the link back in a working state
    env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['failed'] = False

    env.setup_next_link_failure()
