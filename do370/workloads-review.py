#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
# Jul 14 2021 Andres Hernandez <andres.hernandez@redhat.com>
#   - original code
# Aug 19, 2021 Austin Garrigus <agarrigu@redhat.com>
#   - modified for workloads-review
# Sep 02, 2021 Iván Chavero <ichavero@redhat.com>
#   - Refactor workloads-review
# Mar 29, 2022 Andres Hernandez <andres.hernandez@redhat.com>
#   - Full rewrite of the workloads-review lab

"""
Grading module for DO370 workloads-review end of chapter lab.

This module implements the start, grading, and finish actions for the
workloads-review guided exercise.
"""

import os
import sys
import pkg_resources
import logging
import json
import yaml

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
NAMESPACE = "workloads-review"

disable_warnings(InsecureRequestWarning)

class GradingError(Exception):
    pass

# Change the class name to match your file name
class WorkloadsReview(OpenShift):
    """
    workloads-review lab script for DO370
    """
    __LAB__ = "workloads-review"

    # Get the OCP host and port from environment variables
    OCP_API = {
        "user": os.environ.get("OCP_USER", "admin"),
        "password": os.environ.get("OCP_PASSWORD", "redhat"),
        "host": os.environ.get("OCP_HOST", "api.ocp4.example.com"),
        "port": os.environ.get("OCP_PORT", "6443"),
    }

    # Initialize class
    def __init__(self):
        logging.debug("init class")
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
        logging.debug("start()")
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
                "label": "Remove resources",
                "task": self._finish_remove_resources,
                "resources_file": "resources.yaml",
                "fatal": True,
            },
            {
                "label": "Project 'workloads-review' is not present",
                "task": self._check_namespace,
                "fatal": True
            },
            {
                "label": "PVC 'mariadb' is not present",
                "task": self._fail_if_exists,
                "api": "v1",
                "type": "PersistentVolumeClaim",
                "name": "mariadb",
                "namespace": NAMESPACE,
                "fatal": True
            },
            {
                "label": "Deployment 'mariadb' is not present",
                "task": self._fail_if_exists,
                "api": "apps/v1",
                "type": "Deployment",
                "name": "mariadb",
                "namespace": NAMESPACE,
                "fatal": True
            },
            {
                "label": "PVC 'wordpress' is not present",
                "task": self._fail_if_exists,
                "api": "v1",
                "type": "PersistentVolumeClaim",
                "name": "wordpress",
                "namespace": NAMESPACE,
                "fatal": True
            },
            {
                "label": "Deployment 'wordpress' is not present",
                "task": self._fail_if_exists,
                "api": "apps/v1",
                "type": "Deployment",
                "name": "wordpress",
                "namespace": NAMESPACE,
                "fatal": True
            },
            {
                "label": "Copy exercise files",
                "task": labtools.copy_lab_files,
                "lab_name": self.__LAB__,
                "fatal": True
            },
            {
                "label": "Create resources",
                "task": self._start_create_resources,
                "resources_file": "resources.yaml",
                "fatal": True,
            },
        ]
        logging.debug("start()=>run")
        userinterface.Console(items).run_items(action="Starting")

    def grade(self):
        """
        Perform lab grading
        """
        logging.debug("grade()")
        items = [
            {
                "label": "Project 'workloads-review' is present",
                "task": self._fail_if_not_exists,
                "api": "v1",
                "type": "Namespace",
                "name": NAMESPACE,
                "namespace": "",
                "fatal": True
            },
            #   MariaDB
            {
                "label": "PVC 'mariadb' is present",
                "task": self._fail_if_not_exists,
                "api": "v1",
                "type": "PersistentVolumeClaim",
                "name": "mariadb",
                "namespace": NAMESPACE,
                "fatal": True
            },
            {
                "label": 'Check storage class of the "mariadb" PVC',
                "task": self._check_pvc_class,
                "pvc": "mariadb",
                "class": "ocs-storagecluster-ceph-rbd",
                "namespace": NAMESPACE,
                "fatal": True
            },
            {
                "label": "Deployment 'mariadb' is present",
                "task": self._fail_if_not_exists,
                "api": "apps/v1",
                "type": "Deployment",
                "name": "mariadb",
                "namespace": NAMESPACE,
                "fatal": True
            },
            {
                "label": "Deployment 'mariadb' uses the 'mariadb' PVC",
                "task": self._fail_if_not_mounted,
                "deployment": "mariadb",
                "pvc": "mariadb",
                "namespace": NAMESPACE,
                "fatal": True
            },
            #   WordPress
            {
                "label": "PVC 'wordpress' is present",
                "task": self._fail_if_not_exists,
                "api": "v1",
                "type": "PersistentVolumeClaim",
                "name": "wordpress",
                "namespace": NAMESPACE,
                "fatal": True
            },
            {
                "label": 'Check storage class of the "wordpress" PVC',
                "task": self._check_pvc_class,
                "pvc": "wordpress",
                "class": "ocs-storagecluster-cephfs",
                "namespace": NAMESPACE,
                "fatal": True
            },
            {
                "label": "Deployment 'wordpress' is present",
                "task": self._fail_if_not_exists,
                "api": "apps/v1",
                "type": "Deployment",
                "name": "wordpress",
                "namespace": NAMESPACE,
                "fatal": True
            },
            {
                "label": "Deployment 'wordpress' uses the 'wordpress' PVC",
                "task": self._fail_if_not_mounted,
                "deployment": "wordpress",
                "pvc": "wordpress",
                "namespace": NAMESPACE,
                "fatal": True
            },
        ]
        logging.debug("grade()=>run")
        ui = userinterface.Console(items)
        ui.run_items(action="Grading")
        ui.report_grade()

    def finish(self):
        """
        Perform post-lab cleanup
        """
        logging.debug("finish()")
        items = [
            {
                "label": "Checking lab systems",
                "task": labtools.check_host_reachable,
                "hosts": _targets,
                "fatal": True,
            },
            {
                "label": "Remove the 'mariadb' PVC",
                "task": self._delete_resource,
                "api": "v1",
                "type": "PersistentVolumeClaim",
                "name": "mariadb",
                "namespace": NAMESPACE,
                "fatal": False
            },
            {
                "label": "Remove the 'wordpress' PVC",
                "task": self._delete_resource,
                "api": "v1",
                "type": "PersistentVolumeClaim",
                "name": "wordpress",
                "namespace": NAMESPACE,
                "fatal": False
            },
            {
                "label": "Remove resources",
                "task": self._finish_remove_resources,
                "resources_file": "resources.yaml",
                "fatal": True,
            },
            {
                "label": "Remove the 'workloads-review' project",
                "task": self._delete_resource,
                "api": "v1",
                "type": "Namespace",
                "name": NAMESPACE,
                "namespace": ""
            },
            {
                "label": "Remove lab files",
                "task": labtools.delete_workdir,
                "lab_name": self.__LAB__,
                "fatal": True
            },
        ]
        logging.debug("finish()=>run")
        userinterface.Console(items).run_items(action="Finishing")

    ############################################################################
    # Start tasks

    # Create resources from the ~/DO370/solutions/workloads-review/resources.yaml file
    def _start_create_resources(self, item):
        logging.debug("_start_create_resources()")
        lab_name = type(self).__LAB__
        lab_dir = os.path.join(
            pkg_resources.resource_filename(__name__, "materials"),
            "solutions",
            lab_name,
        )
        item["msgs"] = []
        try:
            # Create Project
            project = {
                "apiVersion": "project.openshift.io/v1",
                "kind": "Project",
                "metadata": {
                    "name": NAMESPACE,
                },
            }
            logging.info(
                "Create {}/{}".format(project["kind"], project["metadata"]["name"])
            )
            resource = self.oc_client.resources.get(
                api_version=project["apiVersion"], kind=project["kind"]
            )
            resp = resource.create(body=project, namespace=None)
            item["msgs"].append({"text": "Project"})
            # Create resources from composite yaml file
            resources_file = os.path.join(lab_dir, item["resources_file"])
            logging.info("Creating resources from: {}".format(resources_file))
            with open(resources_file) as input_file:
                content = input_file.read()
                documents = yaml.load_all(content, Loader=yaml.SafeLoader)
                for element in documents:
                    logging.info(
                        "Create {}/{}".format(
                            element["kind"], element["metadata"]["name"]
                        )
                    )
                    resource = self.oc_client.resources.get(
                        api_version=element["apiVersion"], kind=element["kind"]
                    )
                    resp = resource.create(body=element, namespace=NAMESPACE)
            item["msgs"].append({"text": "Lab resources"})
            item["failed"] = False
        except Exception as e:
            exception_name = e.__class__.__name__
            if (exception_name == "ConflictError"):
                logging.info("Element already exists")
                item["failed"] = False
            else:
                item["failed"] = True
                item["msgs"] = [{"text": "Could not create resources"}]
                item["exception"] = {
                    "name": exception_name,
                    "message": str(e),
                }
        return item["failed"]

    def _check_namespace(self, item):
        """
        Check lab namespace
        """
        item["failed"] = False
        if self.resource_exists("v1", "Namespace", NAMESPACE, ""):
            item["failed"] = True
            item["msgs"] = [{"text":
                "The {} project already exists, please ".format(NAMESPACE) +
                "delete it or run 'lab finish {}' ".format(self.__LAB__) +
                "before starting this lab"}]
        return item["failed"]

    def _fail_if_exists(self, item):
        """
        Check resource existence
        """
        item["failed"] = False
        if self.resource_exists(item["api"], item["type"], item["name"], ""):
            item["failed"] = True
            item["msgs"] = [{"text":
                "The {} {} already exists, please ".format(item["name"], item["type"]) +
                "delete it or run 'lab finish {}' ".format(self.__LAB__) +
                "before starting this GE"}]
        return item["failed"]

    ############################################################################
    # Grading tasks

    def _check_pvc_class(self, item):
        try:
            p, c, n = item["pvc"], item["class"], item["namespace"]
            o = self.resource_get("v1", "PersistentVolumeClaim", p, n)
            m = None
            item["failed"] = False
            if not o:
                raise GradingError("PVC {} does not exist.".format(p))
            if o.spec.storageClassName != c:
                raise GradingError("The storage class of {} is incorrect.".format(p))
        except GradingError as e:
            item["failed"] = True
            item["msgs"] = [{"text": "{} Please work through the lab instructions".format(str(e))}]
        return item["failed"]

    def _fail_if_not_exists(self, item):
        """
        Check resource existence
        """
        item["failed"] = False
        if not self.resource_exists(item["api"], item["type"], item["name"], item["namespace"]):
            item["failed"] = True
            item["msgs"] = [{"text":
                "The %s %s does not exist, " % (item["name"], item["type"]) +
                "please work through the lab instructions "}]
        return item["failed"]

    def _fail_if_not_mounted(self, item):
        item["failed"] = False
        try:
            res = self.resource_get("apps/v1", "Deployment", item["deployment"],
                item["namespace"])
            pvc_name = (res.spec.template.spec
                .volumes[0].persistentVolumeClaim.claimName)
            if pvc_name != item["pvc"]:
                raise Exception("PVC {} does not exist.".format(pvc_name))
        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": 
                "'{}' PVC is not mounted on the '{}' deployment, ".format(item["pvc"], item["deployment"]) +
                "please work through the lab instructions."}]
        return item["failed"]

    ############################################################################
    # Finish tasks

    def _delete_resource(self, item):
        item["failed"] = False
        try:
            self.delete_resource(item["api"], item["type"], item["name"], item["namespace"])
        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Failed removing %s: %s" %
                (item["type"], e)}]

    def _finish_remove_resources(self, item):
        logging.debug("_finish_remove_resources()")
        lab_name = type(self).__LAB__
        lab_dir = os.path.join(
            pkg_resources.resource_filename(__name__, "materials"),
            "solutions",
            lab_name,
        )
        item["msgs"] = []
        item["failed"] = False
        # Delete resources from composite yaml file
        resources_file = os.path.join(lab_dir, item["resources_file"])
        logging.info("Deleting resources from: {}".format(resources_file))
        with open(resources_file) as input_file:
            content = input_file.read()
            documents = yaml.load_all(content, Loader=yaml.SafeLoader)
            for element in documents:
                try:
                    logging.info(
                        "Delete {}/{}".format(
                            element["kind"], element["metadata"]["name"]
                        )
                    )
                    resource = self.oc_client.resources.get(
                        api_version=element["apiVersion"], kind=element["kind"]
                    )
                    if element["metadata"].get("namespace", None):
                        resp = resource.delete(name=element["metadata"]["name"], namespace=NAMESPACE)
                    else:
                        resp = resource.delete(name=element["metadata"]["name"])
                except Exception as e:
                    exception_name = e.__class__.__name__
                    if (exception_name == "NotFoundError"):
                        logging.info("Resource was not found")
                        item["failed"] = False
                    else:
                        item["failed"] = True
                        item["msgs"] = [{"text": "Could not delete resources"}]
                        item["exception"] = {
                            "name": exception_name,
                            "message": str(e),
                        }
            item["msgs"].append({"text": "Lab resources"})
        return item["failed"]
