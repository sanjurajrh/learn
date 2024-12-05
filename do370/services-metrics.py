#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
# * Mar 19, 2021 Michael Phillips <miphilli@redhat.com>
#   - original code
# * Aug 02, 2021 Andres Hernandez <andres.hernandez@redhat.com>
#   - Post pilot lab refactor to use OpenShift class from rht-labs-ocp

"""
Grading module for DO370 services-metrics guided exercise.
This module implements the start, grading, and finish actions for the
services-metrics guided exercise.
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
class ServicesMetrics(OpenShift):
    """
    services-metrics lab script for DO370
    """
    __LAB__ = "services-metrics"

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
                "label": "Installing and configuring OpenShift Data Foundation",
                "task": self.run_playbook,
                "playbook": "ansible/install/install-lso-ocs.yml",
                "vars": { "max_device_count": "1" },
                "fatal": True
            },
            {
                "label": "Ensuring Prometheus and Alertmanager use ephemeral storage",
                "task": self.run_playbook,
                "playbook": "ansible/services-metrics/configure-metrics.yml",
                "vars": {"mode": "remove", "prometheusK8s": "{{ default_cluster_service_storage['prometheusK8s'] }}", "alertmanagerMain": "{{ default_cluster_service_storage['alertmanagerMain'] }}" },
                "fatal": True
            },
            {
                "label": "Adding exercise content",
                "task": self.run_playbook,
                "playbook": "ansible/common/add-exercise-dirs.yml",
                "vars": {"exercise": "{{ exercises['services_metrics'] }}"},
                "fatal": True
            },
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
                "vars": {"exercise": "{{ exercises['services_metrics'] }}"},
                "fatal": True
            },
            ####################################################################
            # Uncommenting this block configures Prometheus and Alertmanager to use OCS storage.
            # This block could be added to a different start function if an exercise requires that Prometheus and Alertmanager use OCS storage.
            # {
            #     "label": "Configuring Prometheus and Alertmanager to use storage from OCS",
            #     "task": self.run_playbook,
            #     "playbook": "ansible/services-metrics/configure-metrics.yml",
            #     "vars": {
            #         "mode": "add",
            #         "prometheusK8s": "{{ default_cluster_service_storage['prometheusK8s'] }}",
            #         "alertmanagerMain": "{{ default_cluster_service_storage['alertmanagerMain'] }}"
            #     },
            #     "fatal": True,
            # },
        ]
        logging.debug("About to run the finish tasks")
        userinterface.Console(items).run_items(action="Finishing")
