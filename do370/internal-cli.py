#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
# * Mar 23, 2021 Michael Phillips <miphilli@redhat.com>
#   - changed Instal to Internal to match the course outline
# * Mar 15, 2021 Michael Phillips <miphilli@redhat.com>
#   - original code
# * Jul 28, 2021 Andres Hernandez <andres.hernandez@redhat.com>
#   - Post pilot lab refactor

"""
Grading module for DO370 internal-cli guided exercise.
This module implements the start, grading, and finish actions for the
internal-cli guided exercise.
"""

import os
import sys
import logging

from ocp.utils import OpenShift
from labs import labconfig
from labs.common import labtools, userinterface

# Course SKU
SKU = labconfig.get_course_sku().upper()

# List of hosts involved in that module. Before doing anything,
# the module checks that they can be reached on the network
_targets = ["localhost", "utility"]


# Change the class name to match your file name.
class InternalCLI(OpenShift):
    """
    internal-cli lab script for DO370
    """
    __LAB__ = "internal-cli"

    # Get the OCP host and port from environment variables
    OCP_API = {
        "user": os.environ.get("OCP_USER", None),
        "password": os.environ.get("OCP_PASSWORD", None),
        "host": os.environ.get("OCP_HOST", "api.ocp4.example.com"),
        "port": os.environ.get("OCP_PORT", "6443"),
    }

    # Initialize class
    def __init__(self):
        logging.debug("Initializing super class")
        try:
            super().__init__()
        except Exception as e:
            print("Error: %s" % e)
            sys.exit(1)

    # The following methods define which subcommands are supported
    # (start, grade, finish).

    def start(self):
        """
        Prepare the system for starting the lab
        """
        items = [
            {
                "label": "Checking lab systems",
                "task": labtools.check_host_reachable,
                "hosts": _targets,
                "fatal": True
            },
            {
                "label": "Cluster operators are not progressing",
                "task": self.run_playbook,
                "playbook": "ansible/common/do370-extra.yml",
                "fatal": True
            },
            {
                "label": "Cluster is running and users can log in",
                "task": self.run_playbook,
                "playbook": "ansible/common/ocp4-is-cluster-up.yml",
                "fatal": True
            },
            {
                "label": "Adding exercise content",
                "task": self.run_playbook,
                "playbook": "ansible/common/add-exercise-dirs.yml",
                "vars": {"exercise": "{{ exercises['internal_cli'] }}"},
                "fatal": True
            },
            #{
            #    "label": "Generating sample YAML files",
            #    "task": self.run_playbook,
            #    "playbook": "ansible/install/generate-sample-files.yml"
            #},
        ]
        logging.debug("About to run the start tasks")
        userinterface.Console(items).run_items(action="Starting")

    # grade() is not implemented

    def finish(self):
        """
        Perform post-lab cleanup
        """
        items = [
            {
                "label": "Checking lab systems",
                "task": labtools.check_host_reachable,
                "hosts": _targets,
                "fatal": True
            },
            {
                "label": "Removing exercise content",
                "task": self.run_playbook,
                "playbook": "ansible/common/remove-exercise-dirs.yml",
                "vars": {"exercise": "{{ exercises['internal_cli'] }}"},
                "fatal": True
            },
        ]
        logging.debug("About to run the finish tasks")
        userinterface.Console(items).run_items(action="Finishing")
