#!/usr/bin/env python

####################
# Required Modules #
####################

# Generic/Built-in
import os
from glob import glob
from typing import Tuple

# Libs
import streamlit as st

# Custom
from config import STYLES_DIR
from views.ui_collaboration import app as collab_app
from views.ui_project import app as project_app
from views.ui_experiment import app as expt_app
from views.ui_run import app as run_app
from views.ui_participant import app as participant_app
from views.ui_registration import app as reg_app
from views.ui_inference import app as infer_app
from views.submission import app as submit_app
from views.analysis import app as analysis_app

##################
# Configurations #
##################

# SUPPORTED_DEFAULT_PROCESSES = {
#     # "Construct a deployment script": None
# }

# SUPPORTED_ORCHESTRATOR_PROCESSES = {
#     'collaborations': {'Manage collaboration(s)': collab_app},
#     'projects': {'Manage project(s)': project_app},
#     'experiments': {'Manage experiment(s)': expt_app},
#     "Manage run(s)": run_app,
#     "Submit federated job(s)": submit_app,
#     # "Analyse federated job(s)": analysis_app,
#     # "Optimize a model": None
# }

# SUPPORTED_PARTICIPANT_PROCESSES = {
#     "Manage your profile": participant_app,
#     "Manage your registrations": reg_app,
#     "Submit inference(s)": infer_app
# }

####################
# Helper Functions #
####################

def read_production_css() -> str:
    """ Helper function that loads in and combines all static CSS files 
        declared as a HTML tag string. This is a temporary hack to inject
        custom designs & formats into Streamlit

    Returns:
        Production style tag (str)   
    """
    prod_css_globstring = os.path.join(STYLES_DIR, "**", "*.css") 
    style_paths = glob(prod_css_globstring)

    loaded_styles = []
    for style_path in style_paths:

        with open(style_path, "r") as pcp:
            curr_styles = pcp.read()
            loaded_styles.append(curr_styles)

    production_styles = "<style>{}</style>".format('\n'.join(loaded_styles)) 

    return production_styles


def load_remote_args() -> Tuple[str]:
    """ Helper function that parses incoming query parameters for use in
        subsequent view generations.

    Returns:
        User Role       (str)
        Resource type   (str)
        View type     (str)
    """
    try:
        input_kwargs = st.experimental_get_query_params()
        role = input_kwargs['r'][0]
        resource = input_kwargs['p'][0]
        view = input_kwargs['a'][0]
    except Exception as e:
        st.error("Unable to parse view! Please use the main app.")
        return None
    return role, resource, view


######################################
# Main Synergos UI - Page formatting #
######################################

def main():
    """ Heart of the streamlit App """
    st.set_page_config(layout="wide")

    ###########################
    # Implementation Footnote #
    ###########################

    # [Causes]
    # At the time of development, Streamlit does not have a proper API for
    # specifying custom designs

    # [Problems]
    # Unable to apply custom designs conventionally

    # [Solution]
    # Inject CSS code directly into the HTML template rendered 

    production_styles = read_production_css()
    st.markdown(production_styles, unsafe_allow_html=True) 

    _, resource, requested_view = load_remote_args()

    if resource == "collaborations":
        collab_app(action=requested_view)

    # elif resource == "projects":
    #     project_app(action=requested_view)

    # elif resource == "experiments":
    #     expt_app(action=requested_view)

    # elif resource == "runs":
    #     run_app(action=requested_view)

    # elif resource == "optimizations":
    #     pass

    # elif resource == "analysis":
    #     analysis_app(action=requested_view)

    # elif resource == "profiles":
    #     participant_app(action=requested_view)

    # elif resource == "registrations":
    #     reg_app(action=requested_view)

    # elif resource == "inferences":
    #     infer_app(action=requested_view)


###########
# Scripts #
###########

if __name__ == "__main__":
    main()

