#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
# Jun 15 2021 Andres Hernandez <andres.hernandez@redhat.com>
#   - original code
# Jun 16 2022 Andres Hernandez <andres.hernandez@redhat.com>
#   - Split start/finish functions to create/delete project separately

"""
Grading module for DO370 object-define guided exercise.

This module implements the start, grading, and finish actions for the
object-define guided exercise.
"""

import os
import sys
import pkg_resources
import logging
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
NAMESPACE = "object-define"

disable_warnings(InsecureRequestWarning)

# Change the class name to match your file name
class ObjectDefine(OpenShift):
    """
    object-define lab script for DO370
    """
    __LAB__ = "object-define"

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
                "label": "Project '{}' is not present".format(NAMESPACE),
                "task": self._fail_if_exists,
                "name": NAMESPACE,
                "type": "Project",
                "api": "project.openshift.io/v1",
                "namespace": None,
                "fatal": True
            },
            {
                "label": "Copy exercise files",
                "task": labtools.copy_lab_files,
                "lab_name": self.__LAB__,
                "fatal": True
            },
            {
                "label": "Create project",
                "task": self._start_create_project,
                "fatal": True,
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

    # grade() is not implemented

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
                "label": "Remove resources",
                "task": self._finish_remove_resources,
                "resources_file": "resources.yaml",
                "fatal": True,
            },
            {
                "label": "Remove project",
                "task": self._finish_remove_project,
                "fatal": True,
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

    def _start_create_project(self,item):
        logging.debug("_start_create_project()")
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

    # Create resources from ~/DO370/solutions/object-define/resources.yaml
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
                    # Attempt to get the namespace from the YAML definition
                    # defaults to "None" if it was not defined there
                    # (for cluster wide resources)
                    namespace = element["metadata"].get("namespace", None)
                    # Attempt to create the object and handle exceptions
                    try:
                        resp = resource.create(body=element, namespace=namespace)
                    except Exception as e:
                        exception_name = e.__class__.__name__
                        if (exception_name == "ConflictError"):
                            logging.info("Element already exists")
                        else:
                            logging.debug(exception_name)
                            logging.debug(str(e))
                            raise

            item["msgs"].append({"text": "Lab resources"})
            item["failed"] = False

        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Could not create resources"}]
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
        logging.debug("_finish_remove_resources()")
        lab_name = type(self).__LAB__
        lab_dir = os.path.join(
            pkg_resources.resource_filename(__name__, "materials"),
            "solutions",
            lab_name,
        )
        item["msgs"] = []
        try:
            # Delete resources from composite yaml file
            resources_file = os.path.join(lab_dir, item["resources_file"])
            logging.info("Deleting resources from: {}".format(resources_file))
            with open(resources_file) as input_file:
                content = input_file.read()
                documents = yaml.load_all(content, Loader=yaml.SafeLoader)
                for element in documents:
                    logging.info(
                        "Delete {}/{}".format(
                            element["kind"], element["metadata"]["name"]
                        )
                    )
                    resource = self.oc_client.resources.get(
                        api_version=element["apiVersion"], kind=element["kind"]
                    )
                    # Attempt to get the namespace from the YAML definition
                    # defaults to "None" if it was not defined there
                    # (for cluster wide resources)
                    namespace = element["metadata"].get("namespace", None)
                    try:
                        resp = resource.delete(name=element["metadata"]["name"], namespace=namespace)
                    except Exception as e:
                        exception_name = e.__class__.__name__
                        if (exception_name == "NotFoundError"):
                            logging.info("Resource was not found")
                            item["failed"] = False
                        else:
                            logging.debug(exception_name)
                            logging.debug(str(e))
                            raise

            item["msgs"].append({"text": "Lab resources"})
            item["failed"] = False

        except Exception as e:
            item["failed"] = True
            item["msgs"] = [{"text": "Could not delete resources"}]
            logging.debug("Could not delete resources")
            item["exception"] = {
                "name": e.__class__.__name__,
                "message": str(e),
            }
        return item["failed"]

    def _finish_remove_project(self, item):
        logging.debug("_finish_remove_project()")
        item["msgs"] = []

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
                logging.info("Delete {}/{}".format("project", target))
                resp = resource.delete(name=target)
                item["failed"] = False

            except Exception as e:
                exception_name = e.__class__.__name__
                if (exception_name == "NotFoundError"):
                    logging.info("Resource was not found")
                    item["failed"] = False
                else:
                    item["failed"] = True
                    logging.debug("Could not delete resources")
                    item["msgs"] = [{"text": "Could not delete resources"}]
                    item["exception"] = {
                        "name": exception_name,
                        "message": str(e),
                    }
            item["msgs"].append({"text": "Project"})
        return item["failed"]
