#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
# Jul 01 2021 Andres Hernandez <andres.hernandez@redhat.com>
#   - original code

"""
Grading module for DO370 oadp-stateless guided exercise.

This module implements the start, grading, and finish actions for the
oadp-stateless guided exercise.
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
NAMESPACE = "stateless"

disable_warnings(InsecureRequestWarning)

# Change the class name to match your file name
class OadpStateless(OpenShift):
    """
    oadp-stateless lab script for DO370
    """
    __LAB__ = "oadp-stateless"

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
                "label": "Restore VolumeSnapshotClasses default labels and policies",
                "task": self._start_remove_label_policy,
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
                "label": "Restore VolumeSnapshotClasses default labels and policies",
                "task": self._start_remove_label_policy,
                "fatal": True
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

    def _start_remove_label_policy(self, item):
        try:
            # TODO: Get the VolumeSnapshotClasses names and iterate on them
            for name in [
                "ocs-storagecluster-cephfsplugin-snapclass",
                "ocs-storagecluster-rbdplugin-snapclass"
            ]:
                body = {
                    "apiVersion": "snapshot.storage.k8s.io/v1beta1",
                    "kind": "VolumeSnapshotClass",
                    "metadata": {
                        "name": name,
                        "labels": {
                            # The value is 'None' to delete the label
                            "velero.io/csi-volumesnapshot-class": None
                        }
                    },
                    # Deletion policy can be set to "Delete" (default) or "Retain"
                    "deletionPolicy": "Delete",
                }

                v1_resources = self.oc_client.resources.get(
                    api_version=body["apiVersion"], kind=body["kind"]
                )
                logging.info("Patch {}/{}".format(body["kind"], body["metadata"]["name"]))
                # The content type is required since the resource body is a partial patch
                api_response = v1_resources.patch(
                    body,
                    namespace=None,
                    content_type="application/merge-patch+json"
                )

            item["failed"] = False

        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Could not remove label"}]
            item["exception"] = {
                "name": e.__class__.__name__,
                "message": str(e),
            }
        return item["failed"]

    ############################################################################
    # Grading tasks

    # none

    ############################################################################
    # Finish tasks

    def _finish_remove_resources(self, item):
        for target in ["oadp-operator", NAMESPACE]:
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
