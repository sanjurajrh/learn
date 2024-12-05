#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
# * Jul 29 2021 Iván Chavero ichavero@redhat.com
#   - original code
# * Sep 24 2021 Andrés Hernández <andres.hernandez@redhat.com>
#   - Fixes for release/ODF4.7

"""
Grading module for DO370 comprehensive-review guided exercise (or lab).

This module either does start, grading, or finish for the
comprehensive-review guided exercise (or lab).
"""

import os
import sys
import json

from datetime import datetime
from ocp import api
from ocp import utils
from ocp.utils import OpenShift
from ocp.api import OAuthException
from kubernetes.config.config_exception import ConfigException
from kubernetes.client.rest import ApiException
from labs.grading import Default
from labs.common import labtools, userinterface
import pkg_resources

import logging

_targets = [
    "localhost",
]

# Default namespace for the resources
NAMESPACE = "comprehensive-review"


class ComprehensiveReview(OpenShift):
    """
    Comprehensive Review lab script for DO370
    """
    __LAB__ = "comprehensive-review"

    # Get the OCP host and port from environment variables
    OCP_API = {
        "user": os.environ.get("RHT_OCP4_DEV_USER", None),
        "password": os.environ.get("RHT_OCP4_DEV_PASSWORD", None),
        "host": os.environ.get("OCP_HOST", "api.ocp4.example.com"),
        "port": os.environ.get("OCP_PORT", "6443"),
    }

    materials_dir = os.path.join(
        pkg_resources.resource_filename(__name__, "materials"),
        "labs",
        __LAB__,
    )

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
                "label": "Project 'comprehensive-review' is not present",
                "task": self._fail_if_exists,
                "name": "comprehensive-review",
                "type": "Project",
                "api": "project.openshift.io/v1",
                "namespace": "",
                "fatal": True
            },
            {
                "label": "Copy exercise files",
                "task": labtools.copy_lab_files,
                "lab_name": self.__LAB__,
                "fatal": True,
            },
            {
                "label": "Create the postgresql-persistent-sc template",
                "task": self._start_create_template,
                "fatal": True
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
            {
                "label": "Project 'comprehensive-review' is present",
                "task": self._fail_if_not_exists,
                "name": "comprehensive-review",
                "type": "Project",
                "api": "project.openshift.io/v1",
                "namespace": "",
                "fatal": True
            },
            {
                "label": "Storage class 'ocs-storagecluster-ceph-rbd-xfs' is present",
                "task": self._fail_if_not_exists,
                "type": "StorageClass",
                "api": "storage.k8s.io/v1",
                "name": "ocs-storagecluster-ceph-rbd-xfs",
                "namespace": "openshift-storage",
                "fatal": True
            },
            {
                "label": "PVC 'compreview' is present",
                "task": self._fail_if_not_exists,
                "type": "PersistentVolumeClaim",
                "api": "v1",
                "name": "compreview",
                "namespace": "comprehensive-review",
                "fatal": True
            },
            {
                "label": "PVC 'compreview-file-cephfs' is present",
                "task": self._fail_if_not_exists,
                "type": "PersistentVolumeClaim",
                "api": "v1",
                "name": "compreview-file-cephfs",
                "namespace": "comprehensive-review",
                "fatal": True
            },
            {
                "label": "OBC 'image-object-bucket' is present",
                "task": self._fail_if_not_exists,
                "type": "ObjectBucketClaim",
                "api": "objectbucket.io/v1alpha1",
                "name": "image-object-bucket",
                "namespace": "comprehensive-review",
                "fatal": True
            },
            {
                "label": "VolumeSnapshot 'pg-compreview-snapshot' is present",
                "task": self._fail_if_not_exists,
                "type": "VolumeSnapshot",
                "api": "snapshot.storage.k8s.io/v1",
                "name": "pg-compreview-snapshot",
                "namespace": "comprehensive-review",
                "fatal": True
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
                "label": "Remove 'comprehensive-review' project",
                "task": self._delete_resource,
                "type": "Namespace",
                "api": "v1",
                "name": "comprehensive-review",
                "namespace": ""
            },
            {
                "label": "Delete the 'postgresql-persistent-sc' template",
                "task": self._delete_resource,
                "type": "Template",
                "api": "template.openshift.io/v1",
                "name": "postgresql-persistent-sc",
                "namespace": "openshift",
                "fatal": False,
            },
            {
                "label": "Remove 'compreview' PVC",
                "task": self._delete_resource,
                "type": "PersistentVolumeClaim",
                "api": "v1",
                "name": "compreview",
                "namespace": "comprehensive-review",
                "fatal": False
            },
            {
                "label": "Remove 'compreview-file-cephfs' PVC",
                "task": self._delete_resource,
                "type": "PersistentVolumeClaim",
                "api": "v1",
                "name": "compreview-file-cephfs",
                "namespace": "comprehensive-review",
                "fatal": False
            },
            {
                "label": "Remove 'image-object-bucket' OBC",
                "task": self._delete_resource,
                "type": "ObjectBucketClaim",
                "api": "objectbucket.io/v1alpha1",
                "name": "image-object-bucket",
                "namespace": "comprehensive-review",
                "fatal": False
            },
            {
                "label": "Remove 'ocs-storagecluster-ceph-rbd-xfs' storage class",
                "task": self._delete_resource,
                "type": "StorageClass",
                "api": "storage.k8s.io/v1",
                "name": "ocs-storagecluster-ceph-rbd-xfs",
                "namespace": "openshift-storage",
                "fatal": False
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
            self.delete_resource("v1", "Namespace", "comprehensive-review", "")
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

    def _start_create_template(self, item):
        item["failed"] = False
        try:
            # Create PostgreSQL template
            template_file = os.path.join(self.materials_dir,
                "postgresql-persistent-template-sc.json")
            self._create_from_json_file(template_file,
                "template.openshift.io/v1",
                "Template", "openshift")

        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Could not create the template, " +
                "please run the finish function to cleanup the environment"}]
            item["exception"] = {
                "name": e.__class__.__name__,
                "message": str(e),
            }
        return item["failed"]

    def _create_from_json_file(self, template_file, api_ver, kind, namespace):
        """
        Create a resource from a json file
        TODO: move this one to rht-labs-core api.py
        """
        f = open(template_file)
        t = json.load(f)
        f.close()
        res = self.oc_client.resources.get(
            api_version=api_ver, kind=kind
        )
        resp = res.create(body=t, namespace=namespace)

    # finish
    def _delete_resource(self, item):
        item["failed"] = False
        try:
            self.delete_resource(item["api"], item["type"], item["name"], item["namespace"])
        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Failed removing %s: %s" %
                (item["type"], e)}]
