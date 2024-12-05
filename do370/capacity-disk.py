#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
#   * Fri Jun 04 2021 Iván Chavero ichavero@redhat.com
#   - original code
"""
Grading module for DO370 capacity-disk guided exercise (or lab).

This module either does start, grading, or finish for the
capaticy-extend guided exercise (or lab).
"""

import os
import sys

from datetime import datetime
from ocp import api
from ocp import utils
from ocp.utils import OpenShift
from ocp.api import OAuthException
from kubernetes.config.config_exception import ConfigException
from kubernetes.client.rest import ApiException
from labs.grading import Default
from labs.common import labtools, userinterface

import logging

_targets = [
    "localhost",
]

class CapacityExtend(OpenShift):
    """
    Capacity Disk lab script for DO370
    """
    __LAB__ = "capacity-disk"

    # Get the OCP host and port from environment variables
    OCP_API = {
        "user": os.environ.get("RHT_OCP4_DEV_USER", None),
        "password": os.environ.get("RHT_OCP4_DEV_PASSWORD", None),
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
                "label": "Ping API",
                "task": self._start_ping_api,
                "host": self.OCP_API["host"],
                "fatal": True,
            },
            {
                "label": "Check API",
                "task": self._start_check_api,
                "host": self.OCP_API["host"],
                "port": self.OCP_API["port"],
                "fatal": True,
            },
            {
                "label": "Cluster Ready",
                "task": self._start_check_cluster_ready,
                "fatal": True,
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

    def grade(self):
        """
        Perform evaluation steps on the system
        """
        items = [
            {
                "label": "Checking lab systems",
                "task": labtools.check_host_reachable,
                "hosts": _targets,
                "fatal": True,
            },
        ]
        ui = userinterface.Console(items)
        ui.run_items(action="Grading")
        ui.report_grade()

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
                "label": "Remove exercise files",
                "task": labtools.delete_workdir,
                "lab_name": self.__LAB__,
                "fatal": True,
            }

        ]
        userinterface.Console(items).run_items(action="Finishing")

    def _delete_ge_namespace(self, item):
        item["failed"] = False
        try:
            self.delete_resource("v1", "Namespace", "capacity-disk-ge", "")
        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Failed removing namespace: %s" % e}]

    # Start tasks
    def _start_ping_api(self, item):
        """
        Execute a task to prepare the system for the lab
        """
        if item["host"] is None:
            item["failed"] = True
            item["msgs"] = [{"text": "OCP_HOST is not defined"}]
        else:
            check = labtools.ping(item["host"])
            for key in check:
                item[key] = check[key]

        # Return status to abort lab execution when failed
        return item["failed"]

    def _start_check_api(self, item):
        if item["host"] is None or item["port"] is None:
            item["failed"] = True
            item["msgs"] = [{"text": "OCP_HOST and OCP_PORT are not defined"}]
        else:
            if api.isApiUp(item["host"], port=item["port"]):
                item["failed"] = False
            else:
                item["failed"] = True
                item["msgs"] = [
                    {
                        "text": "API could not be reached: " +
                        "https://{}:{}/".format(item["host"], item["port"])
                    }
                ]

        # Return status to abort lab execution when failed
        return item["failed"]

    def _start_check_cluster_ready(self, item):
        item["failed"] = True
       # Get resources from cluster to check API
        self.oc_client.resources.get(
            api_version="project.openshift.io/v1", kind="Project"
        ).get()
        self.oc_client.resources.get(api_version="v1", kind="Node").get()
        self.oc_client.resources.get(api_version="v1", kind="Namespace").get()

        try:
            v1_config = self.oc_client.resources.get(
                api_version="config.openshift.io/v1", kind="ClusterVersion"
            )
            cluster_version = v1_config.get().items[0]
            if cluster_version.spec.clusterID is None:
                item["failed"] = True
                item["msgs"] = [{"text": "Cluster ID could not be found"}]
            else:
                item["failed"] = False
        except Exception:
            item["msgs"] = [{"text": "Cluster is not OpenShift"}]


    def _check_ge_namespace(self, item):
        """
        Check GE namespace
        """
        item["failed"] = False
        if self.resource_exists("v1", "Namespace", "capacity-disk-ge", ""):
            item["failed"] = True
            item["msgs"] = [{"text":
                "The capacity-disk-ge namespace already exists, please " +
                "delete it or run 'lab finish capacity-disk' " +
                "before starting this GE"}]
        return item["failed"]

