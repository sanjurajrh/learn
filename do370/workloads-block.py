#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
#   * Mon Jul 05 2021 Chris Caillouet ccaillou@redhat.com
#   - Adapted lab script code for workloads-block Guided Exercise

"""
Grading module for DO370 workloads-block guided exercise.

This module either does start, grading, or finish for the
workloads-block guided exercise (or lab).
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
_targets = ["localhost"]

# Default namespace for the resources
NAMESPACE = "workloads-block"

class WorkloadsClasses(OpenShift):
    """
    Workloads Block lab script for DO370
    """
    __LAB__ = "workloads-block"

    # Get the OCP host and port from environment variables
    OCP_API = {
        "user": os.environ.get("OCP_USER", "admin"),
        "password": os.environ.get("OCP_PASSWORD", "redhat"),
        "host": os.environ.get("OCP_HOST", "api.ocp4.example.com"),
        "port": os.environ.get("OCP_PORT", "6443"),
    }

    def __init__(self):
        try:
            super().__init__()
        except Exception as e:
            print("Error: %s" % e)
            sys.exit(1)

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
                "label": "Copy exercise files",
                "task": labtools.copy_lab_files,
                "lab_name": self.__LAB__,
                "fatal": True,
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
                "label": "Remove exercise files",
                "task": labtools.delete_workdir,
                "lab_name": self.__LAB__,
                "fatal": True,
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
        apiVersion = "project.openshift.io/v1"
        kind = "Project"
        name = "workloads-block"
        item["failed"] = False
        if self.resource_exists(apiVersion, kind, name, ""):
            try:
                # Delete Project
                project = {
                    "apiVersion": apiVersion,
                    "kind": kind,
                    "metadata": {
                        "name": name,
                    },
                }
                resource = self.oc_client.resources.get(
                    api_version=apiVersion, kind=kind
                )
                logging.info("Delete project/{}".format(name))
                resp = resource.delete(name=name)
                item["failed"] = False
            except Exception as e:
                exception_name = e.__class__.__name__
                if (exception_name == "NotFoundError"):
                    logging.info("Project/{} was not found".format(name))
                    item["failed"] = False
                else:
                    item["failed"] = True
                    item["msgs"] = [{"text": "Could not delete resources"}]
                    item["exception"] = {
                        "name": exception_name,
                        "message": str(e),
                    }
        return item["failed"]
