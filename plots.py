import time
import typing
import datetime
import logging

import matplotlib
if typing.TYPE_CHECKING:  # avoid circular imports
    from core import Environment
import numpy as np
import networkx as nx
import graph
# mpl.use('agg') #TODO: for use in the command-line-only (no GUI) server
from matplotlib import rcParams
# rcParams['font.family'] = 'sans-serif'
# rcParams['font.sans-serif'] = ['Times New Roman', 'Times']
# rcParams['font.size'] = 24

import matplotlib.pyplot as plt
logging.getLogger('matplotlib').setLevel(logging.WARNING)


def plot_simulation_progress(env: 'Environment'):
    
    """
    Plots results for a particular configuration.
    """
    plt.figure(figsize=(20, 9))

    plt.subplot(3, 3, 1)
    if any(i > 0 for i in env.tracked_results['request_blocking_ratio']):
        plt.semilogy([x * env.track_stats_every for x in range(1, len(env.tracked_results['request_blocking_ratio'])+1)],
                 env.tracked_results['request_blocking_ratio'])
    plt.xlabel('Arrival')
    plt.ylabel('Req. blocking ratio')

    plt.subplot(3, 3, 2)
    plt.plot([x * env.track_stats_every for x in range(1, len(env.tracked_results['average_link_usage'])+1)],
                 env.tracked_results['average_link_usage'])
    plt.xlabel('Arrival')
    plt.ylabel('Avg. link usage')

    plt.subplot(3, 3, 3)
    plt.plot([x * env.track_stats_every for x in range(1, len(env.tracked_results['average_node_usage']) + 1)],
             env.tracked_results['average_node_usage'])
    plt.xlabel('Arrival')
    plt.ylabel('Avg. node usage')

    plt.subplot(3, 3, 4)
    plt.plot([x * env.track_stats_every for x in range(1, len(env.tracked_results['average_availability'])+1)],
                 env.tracked_results['average_availability'])
    plt.xlabel('Arrival')
    plt.ylabel('System avg. availability')

    plt.subplot(3, 3, 5)
    plt.plot([x * env.track_stats_every for x in range(1, len(env.tracked_results['average_restorability'])+1)],
                 env.tracked_results['average_restorability'])
    plt.xlabel('Arrival')
    plt.ylabel('System avg. restorability')
    plt.subplot(3, 3, 6)
    plt.plot([x * env.track_stats_every for x in range(1, len(env.tracked_results['average_relocation'])+1)],
                 env.tracked_results['average_relocation'])
    plt.xlabel('Arrival')
    plt.ylabel('DCs avg. relocation')

    plt.subplot(3, 3, 7)
    plt.plot([x * env.track_stats_every for x in range(1, len(env.tracked_results['avg_expected_loss_cost'])+1)],
                 env.tracked_results['avg_expected_loss_cost'])
    plt.xlabel('Arrival')
    plt.ylabel('Expected capacity loss')
    plt.subplot(3, 3, 8)
    plt.plot([x * env.track_stats_every for x in range(1, len(env.tracked_results['avg_loss_cost'])+1)],
                 env.tracked_results['avg_loss_cost'])
    plt.xlabel('Arrival')
    plt.ylabel('Average loss cost')
    plt.subplot(3, 3, 9)
    plt.plot([x * env.track_stats_every for x in range(1, len(env.tracked_results['avg_expected_loss_cost'])+1)],
                 env.tracked_results['avg_expected_loss_cost'])
    plt.xlabel('Arrival')
    plt.ylabel('Avarage expected loss cost')    
    

    plt.tight_layout()
    # plt.show()
    for format in env.plot_formats:
        
        plt.savefig('./results/{}/progress_{}_{}_{}_{}.{}'.format(env.output_folder,
                                                               env.routing_policy.name, env.restoration_policy.name,
                                                               env.load, env.id_simulation, format))
    plt.close()


def plot_final_results(env: 'Environment', results: dict, start_time: datetime.datetime, save_file=True, show=False, timedelta=None):
    """
    Consolidates the statistics and plots it periodically and at the end of all simulations.
    """
    markers = ['', 'x', 'o', '*']
    line_styles = ['-', '--', ':', '-.']
    plt.figure(figsize=(12, 9))
    plt.subplot(3, 3, 1)
    for id_routing_policy, routing_policy in enumerate(results.keys()):
        for id_restoration_policy, restoration_policy in enumerate(results[routing_policy].keys()):
            if any(results[routing_policy][restoration_policy][load][x]['request_blocking_ratio'] > 0 for load in results[routing_policy][restoration_policy].keys() for x in range(len(results[routing_policy][restoration_policy][load]))):
                plt.semilogy([load for load in results[routing_policy][restoration_policy].keys()],
                [np.mean([results[routing_policy][restoration_policy][load][x]['request_blocking_ratio'] for x in range(len(results[routing_policy][restoration_policy][load]))])
                for load in results[routing_policy][restoration_policy].keys()], label=f"{routing_policy}/{restoration_policy}", marker=markers[id_routing_policy], ls=line_styles[id_restoration_policy])
    plt.xlabel('Load [Erlang]')
    plt.ylabel('Req. blocking ratio')

    plt.subplot(3, 3, 2)
    has_data = False
    for id_routing_policy, routing_policy in enumerate(results.keys()):
        for id_restoration_policy, restoration_policy in enumerate(results[routing_policy].keys()):
            if any(results[routing_policy][restoration_policy][load][x]['average_link_usage'] > 0 for load in results[routing_policy][restoration_policy].keys() for x in range(len(results[routing_policy][restoration_policy][load]))):
                has_data = True
                plt.plot([load for load in results[routing_policy][restoration_policy].keys()],
                    [np.mean([results[routing_policy][restoration_policy][load][x]['average_link_usage'] for x in range(len(results[routing_policy][restoration_policy][load]))]) for
                    load in results[routing_policy][restoration_policy].keys()], label=f"{routing_policy}/{restoration_policy}", marker=markers[id_routing_policy], ls=line_styles[id_restoration_policy])
    plt.xlabel('Load [Erlang]')
    plt.ylabel('Avg. link usage')
    # if has_data:
    #     plt.legend(loc=2)

    plt.subplot(3, 3, 3)
    has_data = False
    for id_routing_policy, routing_policy in enumerate(results.keys()):
        for id_restoration_policy, restoration_policy in enumerate(results[routing_policy].keys()):
            if any(results[routing_policy][restoration_policy][load][x]['average_node_usage'] > 0 for load in results[routing_policy][restoration_policy].keys() for x in
                range(len(results[routing_policy][restoration_policy][load]))):
                has_data = True
                plt.plot([load for load in results[routing_policy][restoration_policy].keys()],
                                [np.mean([results[routing_policy][restoration_policy][load][x]['average_node_usage'] for x in
                                        range(len(results[routing_policy][restoration_policy][load]))]) for
                                load in results[routing_policy][restoration_policy].keys()], label=f"{routing_policy}/{restoration_policy}", marker=markers[id_routing_policy], ls=line_styles[id_restoration_policy])
    plt.xlabel('Load [Erlang]')
    plt.ylabel('Avg. node usage')
    if has_data:
        plt.legend(loc=2)

    plt.subplot(3, 3, 4)
    has_data = False
    for id_routing_policy, routing_policy in enumerate(results.keys()):
        for id_restoration_policy, restoration_policy in enumerate(results[routing_policy].keys()):
            if any(results[routing_policy][restoration_policy][load][x]['average_availability'] > 0 for load in results[routing_policy][restoration_policy].keys() for x in
                range(len(results[routing_policy][restoration_policy][load]))):
                has_data = True
                plt.plot([load for load in results[routing_policy][restoration_policy].keys()],
                                [np.mean([results[routing_policy][restoration_policy][load][x]['average_availability'] for x in
                                        range(len(results[routing_policy][restoration_policy][load]))]) for
                                load in results[routing_policy][restoration_policy].keys()], label=f"{routing_policy}/{restoration_policy}", marker=markers[id_routing_policy], ls=line_styles[id_restoration_policy])
    plt.xlabel('Load [Erlang]')
    plt.ylabel('Avg. availability')

    plt.subplot(3, 3, 5)
    has_data = False
    num_routing_policies = len(results.keys())
    for id_routing_policy, routing_policy in enumerate(results.keys()):
        num_restoration_policies = len(results[routing_policy].keys())
        for id_restoration_policy, restoration_policy in enumerate(results[routing_policy].keys()):
            if any(results[routing_policy][restoration_policy][load][x]['average_restorability'] > 0 for load in results[routing_policy][restoration_policy].keys() for x in
                range(len(results[routing_policy][restoration_policy][load]))):
                has_data = True
                plt.plot([load for load in results[routing_policy][restoration_policy].keys()],
                                [np.mean([results[routing_policy][restoration_policy][load][x]['average_restorability'] for x in
                                        range(len(results[routing_policy][restoration_policy][load]))]) for
                                load in results[routing_policy][restoration_policy].keys()], label=f"{routing_policy}/{restoration_policy}", 
                                marker=markers[id_routing_policy], ls=line_styles[id_restoration_policy])
    plt.xlabel('Load [Erlang]')
    plt.ylabel('Avg. restorability')

    plt.subplot(3, 3, 6)
    has_data = False
    for id_routing_policy, routing_policy in enumerate(results.keys()):
        for id_restoration_policy, restoration_policy in enumerate(results[routing_policy].keys()):
            if any(results[routing_policy][restoration_policy][load][x]['average_relocation'] > 0 for load in results[routing_policy][restoration_policy].keys() for x in
                range(len(results[routing_policy][restoration_policy][load]))):
                has_data = True
                plt.plot([load for load in results[routing_policy][restoration_policy].keys()],
                                [np.mean([results[routing_policy][restoration_policy][load][x]['average_relocation'] for x in
                                        range(len(results[routing_policy][restoration_policy][load]))]) for
                                load in results[routing_policy][restoration_policy].keys()], label=f"{routing_policy}/{restoration_policy}", marker=markers[id_routing_policy], ls=line_styles[id_restoration_policy])
    plt.xlabel('Load [Erlang]')
    plt.ylabel('Avg. relocation')

    #Below are measurements related to cascading failures.

    plt.subplot(3, 3, 7)
    has_data = False
    for id_routing_policy, routing_policy in enumerate(results.keys()):
        for id_restoration_policy, restoration_policy in enumerate(results[routing_policy].keys()):
            if any(results[routing_policy][restoration_policy][load][x]['avg_expected_loss_cost'] > 0 for load in results[routing_policy][restoration_policy].keys() for x in
                range(len(results[routing_policy][restoration_policy][load]))):
                has_data = True
                plt.plot([load for load in results[routing_policy][restoration_policy].keys()],
                                [np.mean([results[routing_policy][restoration_policy][load][x]['avg_expected_loss_cost'] for x in
                                        range(len(results[routing_policy][restoration_policy][load]))]) for
                                load in results[routing_policy][restoration_policy].keys()], label=f"{routing_policy}/{restoration_policy}", marker=markers[id_routing_policy], ls=line_styles[id_restoration_policy])
    plt.xlabel('Load [Erlang]')
    plt.ylabel('Avg. expected capacity loss')
    plt.subplot(3, 3, 8)
    has_data = False
    for id_routing_policy, routing_policy in enumerate(results.keys()):
        for id_restoration_policy, restoration_policy in enumerate(results[routing_policy].keys()):
            if any(results[routing_policy][restoration_policy][load][x]['avg_loss_cost'] > 0 for load in results[routing_policy][restoration_policy].keys() for x in
                range(len(results[routing_policy][restoration_policy][load]))):
                has_data = True
                plt.plot([load for load in results[routing_policy][restoration_policy].keys()],
                                [np.mean([results[routing_policy][restoration_policy][load][x]['avg_loss_cost'] for x in
                                        range(len(results[routing_policy][restoration_policy][load]))]) for
                                load in results[routing_policy][restoration_policy].keys()], label=f"{routing_policy}/{restoration_policy}", marker=markers[id_routing_policy], ls=line_styles[id_restoration_policy])
    plt.xlabel('Load [Erlang]')
    plt.ylabel('Avg. loss cost')
    plt.subplot(3, 3, 9)
    has_data = False
    for id_routing_policy, routing_policy in enumerate(results.keys()):
        for id_restoration_policy, restoration_policy in enumerate(results[routing_policy].keys()):
            if any(results[routing_policy][restoration_policy][load][x]['avg_expected_loss_cost'] > 0 for load in results[routing_policy][restoration_policy].keys() for x in
                range(len(results[routing_policy][restoration_policy][load]))):
                has_data = True
                plt.plot([load for load in results[routing_policy][restoration_policy].keys()],
                                [np.mean([results[routing_policy][restoration_policy][load][x]['avg_expected_loss_cost'] for x in
                                        range(len(results[routing_policy][restoration_policy][load]))]) for
                                load in results[routing_policy][restoration_policy].keys()], label=f"{routing_policy}/{restoration_policy}", marker=markers[id_routing_policy], ls=line_styles[id_restoration_policy])
    plt.xlabel('Load [Erlang]')
    plt.ylabel('Avg. expected loss cost')


    total_simulations = num_routing_policies * num_restoration_policies * env.num_seeds
    performed_simulations = np.sum([len(results[p][l]) for p in results.keys() for l in results[p].keys()])

    percentage_completed = float(performed_simulations) / float(total_simulations) * 100.

    plt.tight_layout()

    if timedelta is None:
        timedelta = datetime.timedelta(seconds=(time.time() - start_time))

    plt.text(0.01, 0.02, 'Progress: {} out of {} ({:.3f} %) / {}'.format(performed_simulations,
                                                        total_simulations,
                                                        percentage_completed,
                                                        timedelta),
                                                        transform=plt.gcf().transFigure,
                                                        fontsize=rcParams['font.size'] - 4.)

    if save_file:
        for format in env.plot_formats:
            plt.savefig('./results/{}/final_results.{}'.format(env.output_folder, format))
    if show:
        plt.show()
    plt.close()


def plot_topology(env: 'Environment', args):
    bbox = dict(boxstyle ="round", fc ="0.7", alpha=0.4)
    plt.figure()
    plt.axis('off')
    pos = nx.get_node_attributes(env.topology, 'pos')

    nx.draw_networkx_edges(env.topology, pos)

    # using scatter rather than nx.draw_networkx_nodes to be able to have a legend in the topology
    nodes_x = [pos[x][0] for x in env.topology.graph['source_nodes']]
    nodes_y = [pos[x][1] for x in env.topology.graph['source_nodes']]
    for idx, node in enumerate(env.topology.graph['source_nodes']):
        ajust = len(node)/2.5
        plt.annotate(node, (nodes_x[idx]-ajust, nodes_y[idx]-1), fontsize=5)
    plt.scatter(nodes_x, nodes_y, label='Node', color='blue', alpha=1., marker='o', linewidths=1., edgecolors='black', s=160.)
    nodes_x = [pos[x][0] for x in env.topology.graph['dcs']]
    nodes_y = [pos[x][1] for x in env.topology.graph['dcs']]
    plt.scatter(nodes_x, nodes_y, label='DC', color='red', alpha=1., marker='s', linewidths=1., edgecolors='black',s=200.)
    
    #Writes dc's name under it
    for idx, dc in enumerate(env.topology.graph['dcs']):
        ajust = len(dc)/2.5
        plt.annotate(dc, (nodes_x[idx]-ajust, nodes_y[idx]-1.1),  bbox = bbox, fontsize=7)

        
    plt.legend(loc=1)
    for format in env.plot_formats:
        plt.savefig(f'./results/{env.output_folder}/topology_{env.topology_name}.{format}')
    plt.close() # avoids too many figures opened at once
    print("plot topology")