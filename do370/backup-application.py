#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
# Jul 14 2021 Andres Hernandez <andres.hernandez@redhat.com>
#   - original code

"""
Grading module for DO370 backup-application guided exercise.

This module implements the start, grading, and finish actions for the
backup-application guided exercise.
"""

import os
import sys
import logging

from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from ocp.utils import OpenShift
from labs import labconfig
from labs.common import labtools, userinterface

# Course SKU
SKU = labconfig.get_course_sku().upper()

# List of hosts involved in that module. Before doing anything,
# the module checks that they can be reached on the network
_targets = ["localhost"]

# Default namespace for the resources
NAMESPACE = "backup-application"

disable_warnings(InsecureRequestWarning)

# Change the class name to match your file name
class BackupApplication(OpenShift):
    """
    backup-application lab script for DO370
    """
    __LAB__ = "backup-application"

    # Get the OCP host and port from environment variables
    OCP_API = {
        "user": os.environ.get("OCP_USER", "admin"),
        "password": os.environ.get("OCP_PASSWORD", "redhat"),
        "host": os.environ.get("OCP_HOST", "api.ocp4.example.com"),
        "port": os.environ.get("OCP_PORT", "6443"),
    }

    # Initialize class
    def __init__(self):
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
                "fatal": True,
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
                "label": "Delete project if exists",
                "task": self._finish_remove_resources
            },
            {
                "label": "Copy exercise files",
                "task": labtools.copy_lab_files,
                "lab_name": self.__LAB__,
                "fatal": True
            },
        ]
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
                "fatal": True,
            },
            {
                "label": "Remove resources",
                "task": self._finish_remove_resources
            },
            {
                "label": "Remove lab files",
                "task": labtools.delete_workdir,
                "lab_name": self.__LAB__,
                "fatal": True
            },
        ]
        userinterface.Console(items).run_items(action="Finishing")

    ############################################################################
    # Start tasks

    # none

    ############################################################################
    # Grading tasks

    # none

    ############################################################################
    # Finish tasks

    def _finish_remove_resources(self, item):
        for target in [NAMESPACE]:
            try:
                # Delete Project
                project = {
                    "apiVersion": "project.openshift.io/v1",
                    "kind": "Project",
                    "metadata": {
                        "name": target,
                    },
                }
                resource = self.oc_client.resources.get(
                    api_version=project["apiVersion"], kind=project["kind"]
                )
                logging.info("Delete project/{}".format(target))
                resp = resource.delete(name=target)

                item["failed"] = False
            except Exception as e:
                exception_name = e.__class__.__name__
                if (exception_name == "NotFoundError"):
                    logging.info("Project/{} was not found".format(target))
                    item["failed"] = False
                else:
                    item["failed"] = True
                    item["msgs"] = [{"text": "Could not delete resources"}]
                    item["exception"] = {
                        "name": exception_name,
                        "message": str(e),
                    }
        return item["failed"]
