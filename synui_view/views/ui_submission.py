#!/usr/bin/env python

####################
# Required Modules #
####################

# Generic/Built-in
import json
import os
from collections import Counter
from typing import Dict, List, Any, Tuple

# Libs
import streamlit as st
import streamlit.components.v1 as components 

# Custom
from config import STYLES_DIR
from synergos import Driver
from views.core.processes import TrackedProcess
from views.utils import (
    is_connection_valid,
    rerun,
    download_button,
    load_custom_css,
    render_orchestrator_inputs,
    render_upstream_hierarchy,
    MultiApp
)

##################
# Configurations #
##################

R_TYPE = "model"

SUPPORTED_DASHBOARDS = ['Launchpad', 'Command Station']
SUPPORTED_COMPONENTS = ['catalogue', 'logger', 'meter', 'mlops', 'mq', 'ui']
SUPPORTED_OPTIONS = ["Preview results", "Download results"]

GLOBAL_CSS_PATH = os.path.join(STYLES_DIR, "custom", "st_global.css")
IFRAME_CSS_PATH = os.path.join(STYLES_DIR, "custom", "st_iframe.css")

PADDING = 28

###########
# Helpers #
###########

def _f(target: str, padding: int = PADDING, postfix: str = ":") -> str:
    """ Helper function to format strings for summary segments

    Args:
        target (str): Target string to be padded
    Returns:
        Padded string (str)
    """
    return target.ljust(padding, " ") + postfix

###############################################
# Submission UI Option - Open command station #
###############################################

def load_command_station(driver: Driver, filters: Dict[str, str]):
    """ Loads up a consoldated view of IFrames of all registered Synergos
        components corresponding to the specified set of filters

    Args:
        driver (Driver): Helper object to facilitate connection
        filters (dict): Composite key set identifying a specific federated job
    """
    load_custom_css(css_path=GLOBAL_CSS_PATH)
    load_custom_css(css_path=IFRAME_CSS_PATH)

    collab_id = filters.get('collab_id', '')
    collab_data = driver.collaborations.read(collab_id).get('data', {})

    if collab_data:

        command_station = components.declare_component(
            "command_station",
            url="http://localhost:3001"
        )
        command_station(
            mlops={
                'name': "MLOps",
                'host': "111.111.111.111",
                'port': 5000,
            },
            logs={
                'name': "Logs",
                'host': "localhost",
                'port': 9000
            },
            mq={
                'name': "MQ",
                'host': "localhost",
                'port': 15672 
            }
        )

    else:
        st.warning(
            f"""
            Specified Collaboration {collab_id} does not exist!

            Please check that you have chosen the correct federated key set before trying again.
            """
        )

#########################################
# Submission UI Option - Open Launchpad #
#########################################

def collate_general_statistics(driver: Driver, filters: Dict[str, str]):
    """ Composes a table of metadata summarizing the general state of jobs &
        resource available for a project under specified collaboration

    Args:
        driver (Driver): Helper object to facilitate connection
        filters (dict): Composite key set identifying a specific federated job
    """
    def count_grids(registry_data: Dict[str, Any]) -> int:
        """ Count number of grids available for use for the current set of 
            filters. This is determined by the number of grids registered 
            across all participants at the specified project level.

        Args:
            registry_data (list): All registration records made by participants
                under the current project
        Returns:
            Grid count (int)            
        """
        node_counts = [reg_record.get('n_count') for reg_record in registry_data]
        grids_available = min(node_counts) if node_counts else 0
        return grids_available

    def count_participants(registry_data: List[Dict[str, Any]]) -> int:
        """ Count number of participants registered under current collaboration

        Args:
            registry_data (list): All registration records made by participants
                under the current project
        Returns:
            Participant count (int)
        """
        return len(registry_data)

    def count_total_jobs(project_data: List[Dict[str, Any]]) -> int:
        """ Count total number of federated jobs submitted under the specified
            project. A job is defined as a unique hierarchical combination
            of collab/proj/expt/run.

        Args:
            run_data (list): All run records registered under specified experiment
        Returns:
            Total count (int)
        """
        run_data = project_data.get('relations', {}).get('Run', [])
        return len(run_data)

    def count_completed_jobs(project_data: List[Dict[str, Any]]) -> int:
        """ Count total number of federated jobs submitted under the specified
            experiment. A job is defined as a unique hierarchical combination
            of collab/proj/expt/run.

        Args:
            model_data (list): All model records created after succcesfully 
                their respective models have been successfully trained
        Returns:
            Completed job count (int)
        """
        model_data = project_data.get('relations', {}).get('Model', [])
        return len(model_data)

    def count_pending_jobs(project_data: List[Dict[str, Any]]) -> int:
        """ Count number of jobs (i.e. unique collab/proj/expt/run id set)
            currently registered under specific project
        """
        return count_total_jobs(project_data) - count_completed_jobs(project_data)

    collab_id = filters.get('collab_id', "")
    project_id = filters.get('project_id', "")

    project_data = driver.projects.read(
        collab_id=collab_id, 
        project_id=project_id
    ).get('data', {})

    registry_data = project_data.get('relations', {}).get('Registration', [])

    grid_count = count_grids(registry_data)
    participant_count = count_participants(registry_data)
    job_count = count_total_jobs(project_data)
    completed_count = count_completed_jobs(project_data)
    pending_count = count_pending_jobs(project_data)

    st.subheader("General")
    st.code(
        "\n".join([
            f"{_f('No. of grids', 24)} {grid_count}",
            f"{_f('No. of participants', 24)} {participant_count}",
            f"{_f('No. of jobs completed', 24)} {completed_count}/{job_count}",
            f"{_f('No. of jobs left', 24)} {pending_count}/{job_count}"
        ])
    )


def collate_participant_statistics(driver: Driver, filters: Dict[str, str]):
    """ Composes a table of metadata summarizing the state of participant-specific 
        resource available for a project under specified collaboration

    Args:
        driver (Driver): Helper object to facilitate connection
        filters (dict): Composite key set identifying a specific federated job
    """
    def count_dataset_partitions(project_data: List[Dict[str, Any]]) -> int:
        """ Counts the total number of dataset partitions across the grid. A
            partition is defined as combinable datasets to represent a single
            participant's dataset. Partition count indirectly represents
            the amount of variation in training data, since each partition
            can constitute non-IID problems as well

        Args:
            project_data (list): All project records created under specified
                collaboration.
        Returns:
            Grid partition count
        """
        tag_data = project_data.get('relations', {}).get('Tag', [])
        grid_partitions = {}
        for tag_record in tag_data:
            for meta in ['train', 'evaluate', 'predict']:
                curr_partitions = len(tag_record.get(meta, []))
                meta_partitions = grid_partitions.get(meta, 0)
                meta_partitions += curr_partitions
                grid_partitions[meta] = meta_partitions

        return grid_partitions

    collab_id = filters.get('collab_id', "")
    project_id = filters.get('project_id', "")

    project_data = driver.projects.read(
        collab_id=collab_id, 
        project_id=project_id
    ).get('data', {})

    action = project_data.get('action')
    grid_partitions = count_dataset_partitions(project_data)

    st.subheader("Participants")
    st.code(
        "\n".join([
            f"{_f('ML operation', 39)} {action}",
            *[
                f"{_f(f'No. of dataset partitions - {meta.upper()}', 39)} {count}"
                for meta, count in grid_partitions.items()
            ]
        ])
    )


def collate_model_statistics(driver: Driver, filters: Dict[str, str]):
    """ Composes a table of metadata summarizing the model performances for the
        project under specified collaboration

    Args:
        driver (Driver): Helper object to facilitate connection
        filters (dict): Composite key set identifying a specific federated job
    """
    def extract_grid_stats(project_data: List[Dict[str, Any]]) -> int:
        """ Analyses and extracts best expt-run combos that give the highest
            averaged metrics across the grid

        Args:
            project_data (list): All project records created under specified
                collaboration.
        Returns:
            Completed job count (int)
        """
        action = project_data.get('action')
        if action == "classify":
            target_metrics = ["accuracy", "roc_auc_score", "pr_auc_score", "f_score"]
        else:
            target_metrics = ["R2", "MSE", "MAE"]

        val_data = project_data.get('relations', {}).get('Validation', [])
        avg_metrics = {}
        for val_record in val_data:
            
            expt_id = val_record.get('key', {}).get('expt_id')
            run_id = val_record.get('key', {}).get('run_id')

            val_stats = val_record.get('evaluate', {}).get('statistics', {})
            for metric, results in val_stats.items():

                if metric in target_metrics:
                    if isinstance(results, list) and results:
                        score = sum(results)/len(results)
                    elif isinstance(results, float):
                        score = results
                    else:
                        score = 0

                    expt_score_collection = avg_metrics.get(expt_id, {})
                    run_score_collection = expt_score_collection.get(run_id, {})
                
                    score_collection = run_score_collection.get(metric, [])
                    score_collection.append(score)

                    run_score_collection[metric] = score_collection
                    expt_score_collection[run_id] = run_score_collection
                    avg_metrics[expt_id] = expt_score_collection

        consolidated_avgs = {}
        for expt, expt_scores in avg_metrics.items():
            for run, run_scores in expt_scores.items():
                for metric, score_collection in run_scores.items():
                    grid_avg = sum(score_collection)/len(score_collection)
                    metric_collection = consolidated_avgs.get(metric, [])
                    metric_collection.append((expt, run, grid_avg))
                    consolidated_avgs[metric] = metric_collection

        best_metrics = {}
        for metric, metric_collection in consolidated_avgs.items():
            best_metrics[metric] = max(metric_collection, key=lambda x: x[-1])

        best_overall = Counter([
            combination[:-1] 
            for combination in list(best_metrics.values())
        ]).most_common()

        return best_metrics, best_overall

    collab_id = filters.get('collab_id', "")
    project_id = filters.get('project_id', "")

    project_data = driver.projects.read(
        collab_id=collab_id, 
        project_id=project_id
    ).get('data', {})

    model_count = len(project_data.get('relations', {}).get('Model', []))
    best_metrics, best_overall = extract_grid_stats(project_data)
    
    best_architectures = list(set([combination[0][0] for combination in best_overall]))

    id_buffer_length = 0
    for (expt_id, run_id, _) in best_metrics.values():
        total_length = len(expt_id) + len(run_id) 
        if total_length > id_buffer_length:
            id_buffer_length = total_length

    st.subheader("Models")
    st.code(
        "\n".join([
            f"{_f('No. of models submitted')} {model_count}",
            f"{_f('  > Best architectures')} {best_architectures}",
            *[
                f"{_f(f'  > Best avg {metric}')} {_f(f'{expt_id} > {run_id}', id_buffer_length+3, '')}   -> {score}"
                for metric, (expt_id, run_id, score) in best_metrics.items()
            ]
        ])
    )


def show_hierarchy(driver: Driver, filters: Dict[str, str]):
    """ List out keyword hierarchy derived from specified filters

    Args:
        driver (Driver): Helper object to facilitate connection
        filters (dict): Composite key set identifying a specific federated job
    """
    collab_id = filters.get('collab_id', "")
    project_id = filters.get('project_id', "")
    expt_id = filters.get('expt_id', "")
    run_id = filters.get('run_id', "")

    h_padding = (" "*13)
    hierarchy_str = "{}\n{}{}|> {}\n{}{}|> {}\n{}{}|> {}".format(
        collab_id, 
        h_padding, " "*4, project_id, 
        h_padding, " "*7, expt_id, 
        h_padding, " "*10, run_id
    )
    st.code(f"{_f('Hierarchy', 12)} {hierarchy_str}")


def perform_healthcheck(driver: Driver, filters: Dict[str, str]) -> Tuple[bool]:
    """ Checks that all registered nodes & components of the system are up
        and ready for incoming connections

    Args:
        driver (Driver): Helper object to facilitate connection
        filters (dict): Composite key set identifying a specific federated job
    """
    def detect_deployed_components(collab_data: Dict[str, Any]) -> List[str]:
        """ Given a collaboration archive, detect which additional Synergos
            components were deployed alongside the main grid

        Args:
            collab_data (list): A single collaboration archive that stores
                connection information of all deployed components
        Returns:
            Detected components (list)
        """
        detected_components = []
        for component in SUPPORTED_COMPONENTS:
           for collab_key, collab_value in collab_data.items():
               if (component in collab_key) and collab_value:
                   detected_components.append(component)
                   break

        return detected_components

    def check_logger_connections(collab_data: Dict[str, Any]) -> bool:
        """ Retrieves logger configurations and tests if connection is active

        Args:
            collab_data (list): A single collaboration archive that stores
                connection information of all deployed components
        Returns:
            Is logger active (bool)
        """
        logger_host = collab_data.get('logger_host', "")
        logger_ports = collab_data.get('logger_ports', {})
        for _, port in logger_ports.items():
            if not is_connection_valid(logger_host, port):
                return False

        return True

    def check_mlops_connection(collab_data: Dict[str, Any]) -> bool:
        """ Retrieves mlops configurations and tests if connection is active

        Args:
            collab_data (list): A single collaboration archive that stores
                connection information of all deployed components
        Returns:
            Is mlops active (bool)
        """
        mlops_host = collab_data.get('mlops_host', "")
        mlops_port = collab_data.get('mlops_port', "")

        if not is_connection_valid(mlops_host, mlops_port):
            return False

        return True

    def check_mq_connection(collab_data: Dict[str, Any]) -> bool:
        """ Retrieves message queue configurations and tests if connection is 
            active

        Args:
            collab_data (list): A single collaboration archive that stores
                connection information of all deployed components
        Returns:
            Is MQ active (bool)
        """
        mq_host = collab_data.get('mq_host', "")
        mq_port = collab_data.get('mq_port', "")

        if not is_connection_valid(mq_host, mq_port):
            return False

        return True

    def check_node_connections(
        registry_data: Dict[str, Any]
    ) -> Dict[int, Dict[str, bool]]:
        """ Runs through all registrations and tests which participants have
            inactive/faulty nodes

        Args:
            registry_data (list): All registration records made by participants
                under the current project
        Returns:
            Participant count (int)
        """
        participant_connections = {}
        for reg_record in registry_data:
            
            participant_id = reg_record.get('key', {}).get('participant_id', "")
            node_count = reg_record.get('n_count', 0)
            for grid_idx in range(node_count):
                
                node_info = reg_record.get(f"node_{grid_idx}")
                node_host = node_info.get('host', "")
                rest_port = node_info.get('f_port', 0)

                is_rest_live = is_connection_valid(node_host, rest_port)
                grid_states = participant_connections.get(grid_idx, {})
                grid_states[participant_id] = is_rest_live
                participant_connections[grid_idx] = grid_states

        return participant_connections

    def parse_state(state: bool) -> str:
        return "online" if state else "unavailable"

    DEPLOYMENT_CHECKERS = {
        SUPPORTED_COMPONENTS[1]: check_logger_connections,
        SUPPORTED_COMPONENTS[3]: check_mlops_connection,
        SUPPORTED_COMPONENTS[4]: check_mq_connection
    }  

    collab_id = filters.get('collab_id', "")
    project_id = filters.get('project_id', "")

    collab_data = driver.collaborations.read(collab_id).get('data', {})
    detected_components = detect_deployed_components(collab_data)
    component_states = {
        component.upper(): parse_state(DEPLOYMENT_CHECKERS[component](collab_data))
        for component in detected_components
    }

    registry_data = driver.registrations.read_all(
        collab_id=collab_id, 
        project_id=project_id
    ).get('data', {})

    participant_connections = check_node_connections(registry_data)
    grid_healthcheck_messages = []
    for grid_idx, node_states in participant_connections.items():
        grid_healthcheck_messages.append(f"  > Grid #{grid_idx}")
        for p_id, state in node_states.items():
            grid_healthcheck_messages.append(f"{_f(f'    | {p_id}', len(p_id)+11)} {parse_state(state)}")

    st.code(
        "\n".join([
            "Health Check",
            
            # Orchestrating components
            f"  > Components ({len(detected_components)})",
            *[
                f"{_f(f'    | Synergos {component}', 25)} {state}"
                for component, state in component_states.items()
            ],
            
            # Grid components
            *grid_healthcheck_messages
        ])
    )

    has_inactive_components = any([
        (not state) for state in list(component_states.keys())
    ])
    has_active_grids = any([
        all(list(grid.values())) 
        for grid in list(participant_connections.values())
    ])

    return has_inactive_components, has_active_grids
 

def load_launchpad(driver: Driver, filters: Dict[str, str]):
    """ Loads up launch page for initializing a federated job. This corresponds
        to Phase 2A > 2B > 3A.

    Args:
        driver (Driver): Helper object to facilitate connection
        filters (dict): Composite key set identifying a specific federated job
    """
    st.title("Orchestrator - Federated Analytics")

    ############################################################
    # Step 1: Summarize metadata about specified federated job #
    ############################################################

    st.header("Summary")

    with st.beta_expander(label="Grid statistics", expanded=True):
        columns = st.beta_columns(2)

        with columns[0]:
            collate_general_statistics(driver, filters)
        with columns[1]:
            collate_participant_statistics(driver, filters)

        collate_model_statistics(driver, filters)

    ###########################################################
    # Step 2: Peform health checks on all deployed components #
    ###########################################################

    job_id = driver.runs.read(**filters).get('data', {}).get('doc_id')
    st.header(f"Job #{job_id}:")

    columns = st.beta_columns((3, 2))

    with columns[0]:
        show_hierarchy(driver, filters)
        has_inactive_components, has_active_grids = perform_healthcheck(driver, filters)

    if has_inactive_components or not has_active_grids:

        with columns[-1]:
            with st.beta_expander(label="Alerts", expanded=True):
                if has_inactive_components:
                    st.error(
                        """
                        One or more of your deployed components cannot be reached! 
                        
                        This could be due to:

                        1. Faulty or misconfigured VMs
                        2. Wrong connection metadata declared

                        Please check and ensure that you have correctly deployed your components.
                        """
                    )
                if not has_active_grids:
                    st.error(
                        """
                        No active grids has been detected!

                        This could be due to:

                        1. Participants having faulty or misconfigured deployments
                        2. Participants registering wrong node connection information

                        Please check and ensure that your participants have correctly deployed their worker nodes.
                        """
                    )
    
    elif not has_inactive_components and has_active_grids:

        fl_job = TrackedProcess(
            driver=driver, 
            p_type="submission", 
            filters=filters
        ) 
        detected_status = fl_job.check()

        with columns[0]:
            manual_status = st.text_input(
                label="Status:", 
                key="process_status", 
                value=detected_status
            )

        idle_key = fl_job.statuses[0]
        in_progress_key = fl_job.statuses[1]
        completed_key = fl_job.statuses[2]

        # Edge 1: Orchestrator is forcing a rerun of a completed job
        if detected_status == completed_key and manual_status == idle_key:

            with columns[1]:
                with st.beta_expander(label="Alerts", expanded=True):
                    st.warning(
                        """
                        You have chosen to override current job state.

                        This will rerun the current federated job.

                        Please confirm to proceed.
                        """
                    )
            with columns[0]:
                is_forced = st.selectbox(
                    label="Are you sure you want to force a rerun?",
                    options=["No", "Yes"],
                    key=f"forced_rerun"
                ) == "Yes"
                
            detected_status = manual_status if is_forced else detected_status
        
        ########################################################################
        # Step 3a: If federated job has already completed, preview & download  #
        ########################################################################

        if detected_status == completed_key:

            trained_model = driver.models.read(**filters).get('data', {})
            valid_stats = driver.validations.read(**filters).get('data', {})

            with columns[0]:
                action = st.radio(
                    label="Select an action:",
                    options=SUPPORTED_OPTIONS,
                    key=f"action"
                )
                
                if action == SUPPORTED_OPTIONS[0]:

                    with st.beta_expander(label="Preview", expanded=False):
                        st.code(
                            json.dumps(valid_stats, sort_keys=True, indent=4),
                            language="json"
                        )

                else:

                    filename = st.text_input(
                        label="Filename:",
                        value=f"RESULTS_{filters['collab_id']}_{filters['project_id']}_{filters['expt_id']}_{filters['run_id']}",
                        help="Specify a custom filename if desired"
                    )
                    download_name = f"{filename}.json"
                    download_tag = download_button(
                        object_to_download={
                            'models': trained_model,
                            'validations': valid_stats 
                        },
                        download_filename=download_name,
                        button_text="Download"
                    )
                    st.markdown(download_tag, unsafe_allow_html=True)

        #########################################################################
        # Step 3b: If federated job is still in progress, alert and do nothing  #
        #########################################################################

        elif detected_status == in_progress_key:

            with columns[1]:
                fl_job.track_access()
                start_time = fl_job.retrieve_start_time()
                access_counts = fl_job.retrieve_access_counts()

                with st.beta_expander(label="Alerts", expanded=True):
                    st.warning(
                        f"""
                        Requested job is still in progress. 
                        
                        Start time              : {start_time}

                        No. of times visited    : {access_counts} 
                        """
                    )

        ####################################################################
        # Step 3c: If federated job has not been trained before, start it  #
        ####################################################################

        elif detected_status == idle_key:

            with columns[0]:
                is_auto_aligned = st.checkbox(
                    label="Perform state auto-alignment",
                    value=True,
                    key=f"auto_alignment"
                )
                is_auto_fixed = st.checkbox(
                    label="Perform architecture auto-fixing",
                    value=True,
                    key=f"auto_fix"
                )
                is_logged = st.checkbox(
                    label="Display logs",
                    value=False,
                    key=f"log_msg"
                )
                is_verbose = False
                if is_logged:
                    is_verbose = st.checkbox(
                        label="Use verbose view",
                        value=is_verbose,
                        key=f"verbose"
                    )

                is_submitted = st.button(label="Start", key=f"start_job")
                if is_submitted:

                    fl_job.start()
                    with st.spinner('Job in progress...'):

                        driver.alignments.create(
                            **filters,
                            auto_align=is_auto_aligned,
                            auto_fix=is_auto_fixed
                        ).get('data', [])

                        driver.models.create(
                            **filters,
                            auto_align=is_auto_aligned,
                            dockerised= True,
                            log_msgs=is_logged,
                            verbose=is_verbose
                        ).get('data', [])

                        driver.validations.create(
                            **filters,
                            auto_align=is_auto_aligned,
                            dockerised= True,
                            log_msgs=is_logged,
                            verbose=is_verbose
                        ).get('data', [])

                    fl_job.stop()
                    st.info("Job Completed! Please refresh to view results.")



#######################################
# Job Submission UI - Page Formatting #
#######################################

def app(action: str):
    """ Main app orchestrating federated job triggers """    

    core_app = MultiApp()
    core_app.add_view(title=SUPPORTED_DASHBOARDS[0], func=load_launchpad)
    core_app.add_view(title=SUPPORTED_DASHBOARDS[1], func=load_command_station)

    driver = render_orchestrator_inputs()

    if driver:
        filters = render_upstream_hierarchy(r_type="model", driver=driver)
        has_filters = any([id for id in list(filters.values())])
 
        if has_filters:
            core_app.run(action)(driver, filters)

        else:
            st.warning(
                """
                Please specify your hierarchy filters to continue.
                
                You will see this message if:

                    1. You have not create any collaborations
                    2. One or more of the IDs you have declared are invalid
                """
            )

    else:
        st.warning(
            """
            Please declare a valid grid connection to continue.
            
            You will see this message if:

                1. You have not declared your grid in the sidebar
                2. Connection parameters you have declared are invalid
            """
        )