#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
# * Mar 15, 2021 Michael Phillips <miphilli@redhat.com>
#   - original code
# * Apr 27, 2021 Michael Phillips <miphilli@redhat.com>
#   - Added code to run playbooks that generate and use custom certificates
# * Apr 29, 2021 Michael Phillips <miphilli@redhat.com>
#   - Added blocks for both PVC (filesystem) and OBC (object) storage
#   - These blocks are commented out, but could be used in other start functions.
# * Jul 30, 2021 Andres Hernandez <andres.hernandez@redhat.com>
#   - Post pilot lab refactor to use OpenShift class from rht-labs-ocp

"""
Grading module for DO370 services-registry guided exercise.
This module implements the start, grading, and finish actions for the
services-registry guided exercise.
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
class ServicesRegistry(OpenShift):
    """
    services-registry lab script for DO370
    """
    __LAB__ = "services-registry"

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
                "label": "Ensuring the image registry uses the 'nfs-storage' storage class",
                "task": self.run_playbook,
                "playbook": "ansible/services-registry/configure-registry.yml",
                "vars": {"configure": "default" },
                "fatal": True
            },
            {
                "label": "Ensuring project 'services-registry' does not exist",
                "task": self.run_playbook,
                "playbook": "ansible/common/remove-resource.yml",
                "vars": {"api_version": "project.openshift.io/v1", "resource_name": "services-registry", "resource_kind": "Project"},
                "fatal": True
            },
            {
                "label": "Verifying worker nodes do not have the 'env' label",
                "task": self.run_playbook,
                "playbook": "ansible/services-registry/cleanup.yml",
                "fatal": True
            },
            {
                "label": "Adding exercise content",
                "task": self.run_playbook,
                "playbook": "ansible/common/add-exercise-dirs.yml",
                "vars": {"exercise": "{{ exercises['services_registry'] }}"},
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
                "vars": {"exercise": "{{ exercises['services_registry'] }}"},
                "fatal": True
            },
            {
                "label": "Removing project 'services-registry'",
                "task": self.run_playbook,
                "playbook": "ansible/common/remove-resource.yml",
                "vars": {"api_version": "project.openshift.io/v1", "resource_name": "services-registry", "resource_kind": "Project"},
                "fatal": True
            },
            {
                "label": "Removing 'env' label from worker nodes",
                "task": self.run_playbook,
                "playbook": "ansible/services-registry/cleanup.yml",
                "fatal": True
            },
            ####################################################################
            # Uncommenting this block would configure the image registry to use filesystem storage from OpenShift Data Foundation.
            # This block could be added to a different start function if an exercise requires that the image registry uses OpenShift Data Foundation storage.
            # Alternatively, you can uncomment this block during testing to verify that the start function cleans up correctly.
            # Filesystem storage is not the recommended storage for the image registry, but it can be configured if desired.
            #
            #{
            #    "label": "Configuring the image registry to use filesystem storage from OpenShift Data Foundation",
            #    "task": self.run_playbook,
            #    "playbook": "ansible/services-registry/configure-registry.yml",
            #    "vars": {"configure": "pvc" },
            #    "fatal": True
            #},
            ####################################################################
            # Uncommenting this block would configure the image registry to use object storage from OpenShift Data Foundation.
            # This block could be added to a different start function if an exercise requires that the image registry uses OpenShift Data Foundation storage.
            # Alternatively, you can uncomment this block during testing to verify that the start function cleans up correctly.
            #
            #{
            #    "label": "Configuring the image registry to use object storage from OpenShift Data Foundation",
            #    "task": self.run_playbook,
            #    "playbook": "ansible/services-registry/configure-registry.yml",
            #    "vars": {"configure": "obc" },
            #    "fatal": True
            #},
        ]
        logging.debug("About to run the finish tasks")
        userinterface.Console(items).run_items(action="Finishing")
