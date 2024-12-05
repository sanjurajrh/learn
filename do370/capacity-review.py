#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
# * Mar 22 2021 Iván Chavero ichavero@redhat.com
#   - original code
"""
Grading module for DO370 capacity-review guided exercise (or lab).

This module either does start, grading, or finish for the
capacity-review guided exercise (or lab).
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
import pkg_resources

import logging
import json

_targets = ["localhost"]

class CapacityReview(OpenShift):
    """
    Capacity Review lab script for DO370
    """
    __LAB__ = "capacity-review"

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
            {
                "label": "Create the 'capacity-review' project",
                "task": self._create_project,
                "fatal": True
            },
            {
                "label": "Create the postgresql-persistent-sc template",
                "task": self._create_template,
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
                "label": "capacity-review-pg deployment exists",
                "task": self._check_pg_deployment,
                "fatal": True,
            },
            {
                "label": "capacity-review-pg PVC is 400 Mi",
                "task": self._check_pvc,
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
                "label": "Delete the 'capacity-review' project",
                "task": self._delete__namespace,
                "fatal": True,
            },
            {
                "label": "Delete the 'postgresql-persistent-sc' template",
                "task": self._delete_template,
                "fatal": False,
            },
            {
                "label": "Delete the 'capacity-extend-ge' PVC",
                "task": self._delete_pvc,
                "fatal": False,
            },
        ]
        userinterface.Console(items).run_items(action="Finishing")

    def _create_project(self, item):
        item["failed"] = False
        try:
            # Create Project
            project = {
                "apiVersion": "project.openshift.io/v1",
                "kind": "Project",
                "metadata": {
                    "name": "capacity-review",
                },
            }
            logging.info("Create {}/{}".format(project["kind"], project["metadata"]["name"]))
            resource = self.oc_client.resources.get(api_version=project["apiVersion"], kind=project["kind"])
            resp = resource.create(body=project, namespace=None)
        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Could not create the project, " +
                "please run the finish function to cleanup the environment"}]
            item["exception"] = {
                "name": e.__class__.__name__,
                "message": str(e),
            }
        return item["failed"]

    def _create_template(self, item):
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

    def _delete__namespace(self, item):
        item["failed"] = False
        try:
            self.delete_resource("v1", "Namespace", "capacity-review", "")
        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Failed removing namespace: %s" % e}]

    def _delete_template(self, item):
        item["failed"] = False
        try:
            self.delete_resource("template.openshift.io/v1", "Template",
                "postgresql-persistent-sc", "openshift")
        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Failed removing Template"}]

    def _delete_pvc(self, item):
        """
        Delete capacity-review-pg PVC
        """
        item["failed"] = False
        try:
            self.delete_resource("v1", "PersistentVolumeClaim",
                "capacity-review-pg", "")
        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Failed removing PVC"}]

    def _check_pg_deployment(self, item):
        """
        Check for deployment: capacity-review-pg
        """
        item["failed"] = True
        if self.resource_exists("v1", "DeploymentConfig", "capacity-review-pg", "capacity-review"):
            item["failed"] = False
        else:
            item["msgs"] = [{"text":
                "The capacity-review-pg DeploymentConfig does not exist, " +
                "please complete the review lab"}]
        return item["failed"]

    def _check_pvc(self, item):
        """
        Check for PVC: capacity-review-pg
        """
        item["failed"] = True
        pvc = self.resource_get("v1", "PersistentVolumeClaim", "capacity-review-pg", "capacity-review")
        if pvc:
            size = pvc.spec.resources.requests.storage
            if size != "400Mi":
                item["msgs"] = [{"text":
                    "The capacity-review-pg PVC is not the correct size, please " +
                    "complete the review lab"}]
            else:
                item["failed"] = False
        return item["failed"]

    def _check_template(self, item):
        """
        Check for lab namespace: capacity-review
        """
        item["failed"] = False
        if self.resource_exists("template.openshift.io/v1", "Template", "postgresql-persistent-sc", "openshift"):
            item["failed"] = True
            item["msgs"] = [{"text":
                "The postgresql-persistent-sc template already exists, please " +
                "delete it or run 'lab finish capacity-review' " +
                "before starting this GE"}]
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
