#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
#   * Thu Mar 28 2021 Iván Chavero ichavero@redhat.com
#   * Mon Mar 22 2021 Iván Chavero ichavero@redhat.com
#   - original code
"""
Grading module for DO370 capacity-monitoring guided exercise (or lab).

This module either does start, grading, or finish for the
capaticy-monitoring guided exercise (or lab).
"""

#########################################################################
#                   How to use this template:
#
# 1. Rename the file to SomethingRelatedToYourLab.py. Use WordCaps,
#    do not use dashes or underscores.
# 2. Adjust the CHANGELOG and docstring above.
# 3. Define the hosts that are used in this activity in the _targets list.
# 4. Rename the class. The name of the class must match the file name
#    (without the .py extension)
# 5. Remove the methods (start, finish, or grade) that your lab script
#    does not support.
# 6. Remove these "How to use this template" comments
#########################################################################

# TODO: Implement common file copy wrapper functions

import os
import sys
import pkg_resources

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

# List of hosts involved in that module. Before doing anything,
# the module checks that they can be reached on the network
_targets = [
    "localhost",
]

class CapaticyMonitoring(OpenShift):
    """
    Example OpenShift lab script for DO370
    """
    __LAB__ = "capacity-monitoring"

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
                "label": "Create namespace",
                "task": self._create_ge_namespace,
                "fatal": True,
            },
            {
                "label": "Setup persitent volume claim",
                "task": self._create_pvc,
                "fatal": True,
            },
            {
                "label": "Create pod",
                "task": self._create_pod,
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
                "label": "Delete persitent volume claim",
                "task": self._delete_pvc,
                "fatal": True,
            },
            {
                "label": "Delete the monitoring-ge namespace",
                "task": self._delete_ge_namespace,
                "fatal": True,
            },
        ]
        userinterface.Console(items).run_items(action="Finishing")



    def _delete_ge_namespace(self, item):
        item["failed"] = False
        try:
            self.delete_resource("v1", "Namespace", "monitoring-ge", "")
        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Failed removing namespace: %s" % e}]

    def _delete_pvc(self, item):
        item["failed"] = False
        try:
            self.delete_resource("v1", "PersistentVolumeClaim", "monitoring-ge-pvc", "monitoring-ge")
        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Failed removing PVC"}]


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


    def _create_ge_namespace(self, items):
        """
        Create GE namespace
        """
        body = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": "monitoring-ge"},
            "spec": {}
        }

        rc = self.oc_client.resources.get(
            api_version=body["apiVersion"], kind=body["kind"]
        )
        # If the namespace exists don't complain
        try:
            response = rc.create(body=body, namespace="default")
        except Exception as e:
            pass

    def _create_pvc(self, item):
        # Create PV
        """
        Create PVC
        """
        item["failed"] = False
        body = {
            "kind": "PersistentVolumeClaim",
            "apiVersion": "v1",
            "metadata": {
                "name": "monitoring-ge-pvc",
                "namespace": "monitoring-ge",
            },
            "spec": {
                "accessModes": [
                    "ReadWriteOnce"
                ],
                "resources": {
                    "requests": {
                        "storage": "150M",
                    }
                },
                "storageClassName": "ocs-storagecluster-ceph-rbd"
            },
        }
        rc = self.oc_client.resources.get(
            api_version=body["apiVersion"], kind=body["kind"]
        )

        # Complain if the resource exists
        try:
            response = rc.create(body=body, namespace=body["metadata"]["namespace"])
        except:
            item["failed"] = True
            item["msgs"] = [{"text":
                "Persistent volume claim already exists, please run the finish " +
                "option to clean the environment"}]
            return item["failed"]

    def _create_pod(self, items):
        """
        Create Pod that fills the PCV space
        """
        name = "monitoring-ge-pod"
        body = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": name,
                "namespace": "monitoring-ge",
            },
            "spec": {
                "volumes": [{
                    "name": "monitoring-ge-storage",
                    "persistentVolumeClaim": {
                        "claimName": "monitoring-ge-pvc"
                    }
                }],
                "containers": [{
                    "image": "registry.access.redhat.com/ubi8/ubi-minimal:latest",
                    "name": name,
                    "args": [
                        "/bin/sh",
                        "-c",
                        "dd if=/dev/zero of=/mnt/bigfile count=1 bs=20M; while [ 1 ]; do df -h; sleep 30;done"
                    ],
                    "volumeMounts": [{
                        "mountPath": "/mnt",
                        "name": "monitoring-ge-storage"
                    }]
                }]
            }
        }

        rc = self.oc_client.resources.get(
            api_version=body["apiVersion"], kind=body["kind"]
        )

        #If the pod exists don't complain
        try:
            resp = rc.create(body=body, namespace="monitoring-ge")
        except Exception as e:
            print("Error creating namespace: %s" % e)

        self.wait_for_resource(body['apiVersion'], body['kind'], name, "monitoring-ge")


