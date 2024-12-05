#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
# * Jul 28, 2021 Austin Garrigus <agarrigu@redhat.com>
#   - original code
# * Aug 02, 2021 Andres Hernandez <andres.hernandez@redhat.com>
#   - Take over

"""
Grading module for DO370 services-review guided exercise.
This module implements the start, grading, and finish actions for the
services-review guided exercise.
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
_targets = ["localhost", "utility"]

# Default namespace for the resources
NAMESPACE = "openshift-image-registry"

disable_warnings(InsecureRequestWarning)

# TODO: Change this to LabError
class GradingError(Exception):
    pass

# Change the class name to match your file name.
class ServicesReview(OpenShift):
    """
    services-review lab script for DO370
    """
    __LAB__ = "services-review"

    # Get the OCP host and port from environment variables
    OCP_API = {
        "user": os.environ.get("OCP_USER", "admin"),
        "password": os.environ.get("OCP_PASSWORD", "redhat"),
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
                "label": "Ensuring project 'services-review' does not exist",
                "task": self.run_playbook,
                "playbook": "ansible/common/remove-resource.yml",
                "vars": {"api_version": "project.openshift.io/v1", "resource_name": "services-review", "resource_kind": "Project"},
                "fatal": True
            },
            {
                "label": "Verifying worker nodes do not have the 'env' label",
                "task": self.run_playbook,
                "playbook": "ansible/services-registry/cleanup.yml",
                "fatal": True
            },
            {
                "label": "Copy exercise files",
                "task": labtools.copy_lab_files,
                "lab_name": self.__LAB__,
                "fatal": True,
            },
        ]
        logging.debug("About to run the start tasks")
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
                "label": 'Checking OBC "noobaa-review"',
                "task": self._check_obc_class,
                "obc": "noobaa-review",
                "namespace": NAMESPACE,
                "class": "openshift-storage.noobaa.io",
                "fatal": True,
            },
            {
                "label": "Checking image registry config",
                "task": self._check_cluster_imageregistry,
                "fatal": True,
            },
            {
                "label": 'Checking app "hello-world"',
                "task": self._check_app_exists,
                "app": "hello-world",
                "namespace": "services-review",
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
        logging.debug("About to run the finish tasks")
        userinterface.Console(items).run_items(action="Finishing")

    ############################################################################
    # Start tasks

    # none

    ############################################################################
    # Grading tasks

    def _check_obc_class(self, item):
        try:
            p, c, n = item["obc"], item["class"], item["namespace"]
            o = self.resource_get("v1alpha1", "ObjectBucketClaim", p, n)
            item["failed"] = False
            if not o:
                raise GradingError("OBC {} does not exist.".format(p))
            if o.spec.storageClassName != c:
                raise GradingError("The storage class of {} is incorrect.".format(p))
        except GradingError as e:
            item["failed"] = True
            item["msgs"] = [{"text": "{} Please work through the lab instructions.".format(str(e))}]
        return item["failed"]

    def _check_cluster_imageregistry(self, item):
        try:
            o = self.resource_get("imageregistry.operator.openshift.io/v1", "Config", "cluster", "")

            item["failed"] = False
            if not o:
                raise GradingError("Something went really wrong.")
            if "noobaa-review-" not in o.spec.storage.s3.bucket:
                raise GradingError("Image registry is set to the wrong value.")
        except AttributeError:
            item["failed"] = True
            item["msgs"] = [{"text": "Image registry is not configured. Please work through the lab instructions."}]
        except GradingError as e:
            item["failed"] = True
            item["msgs"] = [{"text": "{} Please work through the lab instructions.".format(str(e))}]
        return item["failed"]

    def _check_app_exists(self, item):
        try:
            a, n = item["app"], item["namespace"]
            o = self.resource_get("v1", "Deployment", a, n)
            item["failed"] = False
            if not o:
                raise GradingError("{} does not exist within namespace {}.".format(a, n))
        except GradingError as e:
            item["failed"] = True
            item["msgs"] = [{"text": "{} Please work through the lab instructions.".format(str(e))}]
        return item["failed"]

    ############################################################################
    # Finish tasks

    # none
