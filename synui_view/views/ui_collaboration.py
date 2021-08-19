#!/usr/bin/env python

####################
# Required Modules #
####################

# Generic/Built-in


# Libs
import streamlit as st

# Custom
from synergos import Driver
from views.renderer import CollaborationRenderer
from views.utils import (
    download_button,
    is_request_successful,
    render_id_generator,
    render_orchestrator_inputs,
    render_confirmation_form,
    render_collaborations,
    render_projects,
    render_experiments,
    render_runs,
    render_orchestrator_registrations,
    MultiApp,
)

##################
# Configurations #
##################

SUPPORTED_ACTIONS = [
    "Create new collaboration(s)",
    "Browse existing collaboration(s)",
    "Update existing collaboration(s)",
    "Remove existing collaboration(s)"
]

DEFAULT_DEPLOYMENTS = {
    'Basic': [],
    'Monitored SME': [
        "Synergos Logger",
        # "Synergos Meter",
        "Synergos MLOps"
    ],
    'SynCluster': [
        # "Synergos Catalogue",
        "Synergos Logger",
        # "Synergos Meter",
        "Synergos MLOps",
        "Synergos MQ"
    ]
}

R_TYPE = "collaboration"

collab_renderer = CollaborationRenderer()

###########
# Helpers #
###########

# def download_ttp_script():

#     script = "docker run \
#             -p 5000:5000 \
#             -v /home/aisg/Desktop/synergos_demos/ttp_data/:/ttp/data \
#             -v /home/aisg/Desktop/synergos_demos/ttp_outputs/:/ttp/outputs \
#             -v /home/aisg/Desktop/synergos_demos/mlflow_test/:/ttp/mlflow \
#             --rm \
#             --name ttp_syncluster_1 \
#             synergos_ttp:basic \
#                 --id ttp_syncluster_1 \
#                 --logging_variant graylog 172.20.0.4 9300 \
#                 --debug \
#                 --censored"

#     with left_column:
#         is_downloaded = st.checkbox(label="Export architecture")
    
#     with right_column:
#         if is_downloaded:
#             filename = st.text_input(
#                 label="Filename:",
#                 value=f"ARCH_{collab_id}_{project_id}_{expt_id}",
#                 help="Specify a custom filename if desired"
#             )
#             is_pickled = st.checkbox('Save as pickle file')
#             download_name = (
#                 f"{filename}.pkl" 
#                 if is_pickled 
#                 else f"{filename}.json"
#             )
#             download_tag = download_button(
#                 object_to_download=model,
#                 download_filename=download_name,
#                 button_text="Download"
#             )
#             st.markdown(download_tag, unsafe_allow_html=True)


#########################################################
# Collaboration UI Option - Create new Collaboration(s) #
#########################################################

def create_collaborations(driver: Driver = None):
    """ Main function that governs the creation of collaborations within a
        specified Synergos network
    """       
    st.title(f"Orchestrator - {SUPPORTED_ACTIONS[0]}")

    ########################
    # Step 0: Introduction #
    ########################


    ##############################################
    # Step 1: Declare orchestrator configuration #
    ##############################################

    st.header("Step 1: Declare your collaboration configuration")

    collab_id = render_id_generator(r_type=R_TYPE)

    columns = st.beta_columns(3)

    synergos_variant = columns[0].selectbox(
        label="Variant:",
        options=list(DEFAULT_DEPLOYMENTS.keys()),
        help="Declare which variant of Synergos you deployed for this collaboration."
    )

    deployment_mode = columns[1].selectbox(
        label="Mode:",
        options=["local", "distributed"],
        help="""Declare which setting was Synergos deployed in. Selecting 
        'local' indicates that all components have been deployed onto the 
        same server. Conversely, selecting 'distributed' indicates a more 
        complex network deployed."""
    )

    default_host = "localhost" if deployment_mode == 'local' else ""

    orchestrator_options = ["TTP" if synergos_variant != "SynCluster" else "Director"]
    orchestrator_deployed = columns[2].selectbox(
        label="Orchestrator Type", 
        options=orchestrator_options,
        help="Orchestrator type will be dynamically inferred given your specified variant."
    )

    ###########################################
    # Step 2: Declare all deployed components #
    ########################################### 

    st.header("Step 2: Declare additional components for your collaboration")

    optional_components_deployed = st.multiselect(
        label="Supplementary components deployed for collaboration:", 
        options=[
            # "Synergos Catalogue",
            "Synergos Logger",
            # "Synergos Meter",
            "Synergos MLOps",
            "Synergos MQ",
            # "Synergos UI"
        ], 
        default=DEFAULT_DEPLOYMENTS[synergos_variant],
        help="Declare which Addons were deployed alongside the core components."
    )

    collab_task = driver.collaborations
    for idx, component in enumerate(optional_components_deployed, start=1):

        st.markdown(f"{idx}. Register specs for {component}:")
        
        if component == "Synergos Catalogue":
            catalogue_info = collab_renderer.render_catalogue_metadata()
            collab_task.configure_catalogue(
                host=catalogue_info['catalogue_host'], 
                port=catalogue_info['catalogue_port']
            )

        elif component == "Synergos Logger":
            logger_info = collab_renderer.render_logger_metadata()
            logger_ports = logger_info['logger_ports']
            collab_task.configure_logger(
                host=logger_info['logger_host'], 
                sysmetrics_port=logger_ports['sysmetrics'],
                director_port=logger_ports['director'],
                ttp_port=logger_ports['ttp'],
                worker_port=logger_ports['worker']
            )

        elif component == "Synergos Meter":
            meter_info = collab_renderer.render_meter_metadata()
            collab_task.configure_meter(
                host=meter_info['meter_host'], 
                port=meter_info['meter_port']
            )

        elif component == "Synergos MLOps":
            mlops_info = collab_renderer.render_mlops_metadata()
            collab_task.configure_mlops(
                host=mlops_info['mlops_host'], 
                port=mlops_info['mlops_port']
            )

        elif component == "Synergos MQ":
            mq_info = collab_renderer.render_mq_metadata()
            collab_task.configure_mq(
                host=mq_info['mq_host'], 
                port=mq_info['mq_port']
            )

        elif component == "Synergos UI":
            ui_info = collab_renderer.render_ui_metadata()
            collab_task.configure_ui(
                host=ui_info['ui_host'], 
                port=ui_info['ui_port']
            )

    ##################################
    # Step 3: Register collaboration #
    ##################################

    st.header("Step 3: Submit your collaboration entry")
    collaboration_configurations = collab_task._compile_configurations()
    is_confirmed = render_confirmation_form(
        data=collaboration_configurations,
        r_type=R_TYPE,
        r_action="creation",
        use_warnings=False    
    )
    if is_confirmed:
        create_resp = collab_task.create(collab_id=collab_id)
        is_request_successful(create_resp)


##############################################################
# Collaboration UI Option - Browse Existing Collaboration(s) #
##############################################################

def browse_collaborations(driver: Driver = None):
    """ Main function that governs the browsing of collaborations within a
        specified Synergos network
    """
    st.title(f"Orchestrator - {SUPPORTED_ACTIONS[1]}")

    ########################
    # Step 0: Introduction #
    ########################


    ######################################################################
    # Step 1: Pull collaboration information from specified orchestrator #
    ######################################################################

    st.header("Step 1: Select your collaboration of interest")
    selected_collab_id, _ = render_collaborations(driver=driver)

    ########################################################################
    # Step 2: Pull associations & relationships of specified collaboration #
    ########################################################################

    st.header("Step 2: Explore Relationships & Associations")
    selected_project_id, _ = render_projects(
        driver=driver, 
        collab_id=selected_collab_id
    )

    selected_expt_id, _ = render_experiments(
        driver=driver, 
        collab_id=selected_collab_id,
        project_id=selected_project_id
    )
    
    render_runs(
        driver=driver, 
        collab_id=selected_collab_id,
        project_id=selected_project_id,
        expt_id=selected_expt_id
    )

    ###########################################################
    # Step 3: Browse registrations of specified collaboration #
    ###########################################################

    st.header("Step 3: Browse Participant Registry")
    render_orchestrator_registrations(
        driver=driver,
        collab_id=selected_collab_id,
        project_id=selected_project_id
    )



##############################################################
# Collaboration UI Option - Update existing collaboration(s) #
##############################################################

def update_collaborations(driver: Driver = None):
    """ Main function that governs the updating of metadata in a collaborations 
        within a specified Synergos network
    """
    st.title(f"Orchestrator - {SUPPORTED_ACTIONS[2]}")

    ######################################################################
    # Step 1: Pull collaboration information from specified orchestrator #
    ######################################################################

    st.header("Step 1: Modify your collaboration of interest")
    selected_collab_id, updated_collab = render_collaborations(driver=driver)
                
    ##################################
    # Step 2: Register collaboration #
    ##################################

    st.header("Step 2: Submit your collaboration entry")
    is_confirmed = render_confirmation_form(
        data=updated_collab,
        r_type=R_TYPE,
        r_action="update",
        use_warnings=False    
    )
    if is_confirmed:
        update_resp = driver.collaborations.update(
            collab_id=selected_collab_id, 
            **updated_collab
        )
        is_request_successful(update_resp)


##############################################################
# Collaboration UI Option - Remove existing collaboration(s) #
##############################################################

def remove_collaborations(driver: Driver = None):
    """ Main function that governs the deletion of metadata in a collaborations 
        within a specified Synergos network
    """
    st.title(f"Orchestrator - {SUPPORTED_ACTIONS[3]}")

    ######################################################################
    # Step 1: Pull collaboration information from specified orchestrator #
    ######################################################################

    st.header("Step 1: Target your collaboration of interest")
    selected_collab_id, updated_collab = render_collaborations(driver=driver)
                
    ################################
    # Step 2: Remove collaboration #
    ################################

    st.header("Step 2: Submit removal request for collaboration ")
    is_confirmed = render_confirmation_form(
        data=updated_collab,
        r_type=R_TYPE,
        r_action="removal",
        use_warnings=True    
    )
    if is_confirmed:
        delete_resp = driver.collaborations.delete(collab_id=selected_collab_id)
        is_request_successful(delete_resp)



######################################
# Collaboration UI - Page Formatting #
######################################

def app(action: str):
    """ Main app orchestrating collaboration management procedures """
    
    core_app = MultiApp()
    core_app.add_view(title=SUPPORTED_ACTIONS[0], func=create_collaborations)
    core_app.add_view(title=SUPPORTED_ACTIONS[1], func=browse_collaborations)
    core_app.add_view(title=SUPPORTED_ACTIONS[2], func=update_collaborations)
    core_app.add_view(title=SUPPORTED_ACTIONS[3], func=remove_collaborations)

    driver = render_orchestrator_inputs()

    if driver:
        core_app.run(action)(driver)

    else:
        st.warning(
            """
            Please declare a valid grid connection to continue.
            
            You will see this message if:

                1. You have not declared your grid in the sidebar
                2. Connection parameters you have declared are invalid
            """
        )
