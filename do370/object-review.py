#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
# Aug 20 2021 Andres Hernandez <andres.hernandez@redhat.com>
#   - original code
# Jun 16 2022 Andres Hernandez <andres.hernandez@redhat.com>
#   - Split start/finish functions to create/delete project separately

"""
Grading module for DO370 object-review guided exercise.

This module implements the start, grading, and finish actions for the
object-review guided exercise (or lab).
"""

import os
import sys
import base64
import subprocess
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
NAMESPACE = "bucket-review"

disable_warnings(InsecureRequestWarning)

# Change the class name to match your file name
class ObjectReview(OpenShift):
    """
    object-review lab script for DO370
    """

    __LAB__ = "object-review"

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
                "fatal": True,
            },
            {
                "label": "Cluster is running and users can log in",
                "task": self.run_playbook,
                "playbook": "ansible/common/ocp4-is-cluster-up.yml",
                "fatal": True,
            },
            {
                "label": "Installing and configuring OpenShift Data Foundation",
                "task": self.run_playbook,
                "playbook": "ansible/install/install-lso-ocs.yml",
                "vars": {"max_device_count": "1"},
                "fatal": True,
            },
            {
                "label": "Remove resources",
                "task": self._finish_remove_resources,
                "resources_file": "s3-app-resources.yaml",
                "fatal": True,
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
                "label": "Remove lab files",
                "task": labtools.delete_workdir,
                "lab_name": self.__LAB__,
                "fatal": True,
            },
            {
                "label": "Copy exercise files",
                "task": labtools.copy_lab_files,
                "lab_name": self.__LAB__,
                "fatal": True,
            },
            {
                "label": "Create project",
                "task": self._start_create_project,
                "fatal": True,
            },
            {
                "label": "Create resources",
                "task": self._start_create_resources,
                "resources_file": "s3-app-resources.yaml",
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
                "label": "Checking lab systems",
                "task": labtools.check_host_reachable,
                "hosts": _targets,
                "fatal": True,
            },
            {
                "label": "Check resources",
                "task": self._grade_test,
                "fatal": True,
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
                "label": "Remove resources",
                "task": self._finish_remove_resources,
                "resources_file": "s3-app-resources.yaml",
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
                "fatal": True,
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

    # Create resources from ~/DO370/solutions/object-review/s3-app-resources.yaml
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

    def _pip_install(self, package):
        return subprocess.run(
            ["pip", "-qqq", "--no-input", "--no-color", "install", package],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _grade_test(self, item):
        logging.debug("_grade_test()")
        self._pip_install("awscli")
        try:
            # Check if the obc/object-review exists
            logging.info("Get {}/{}".format("ObjectBucketClaim", "object-review"))
            obc = self.oc_client.resources.get(
                api_version="objectbucket.io/v1alpha1",
                kind="ObjectBucketClaim"
            ).get(name="object-review", namespace=NAMESPACE)

            # Check if the deployment/photo-album exists
            logging.info("Get {}/{}".format("Deployment", "photo-album"))
            deployment = self.oc_client.resources.get(
                api_version="apps/v1",
                kind="Deployment"
            ).get(name="photo-album", namespace=NAMESPACE)

            # Get the configmap and secret associated with the OBC
            logging.info("Get {}/{}".format("ConfigMap", "object-review"))
            configmap = self.oc_client.resources.get(
                api_version="v1",
                kind="ConfigMap"
            ).get(name="object-review", namespace=NAMESPACE)

            logging.info("Get {}/{}".format("Secret", "object-review"))
            secret = self.oc_client.resources.get(
                api_version="v1",
                kind="Secret"
            ).get(name="object-review", namespace=NAMESPACE)

            # Get the external URL for the Ceph RGW S3 endpoint
            # route/ocs-storagecluster-cephobjectstore -n openshift-storage

            logging.info("Get {}/{}".format("Route", "ocs-storagecluster-cephobjectstore"))
            route = self.oc_client.resources.get(
                api_version="route.openshift.io/v1",
                kind="Route"
            ).get(name="ocs-storagecluster-cephobjectstore", namespace="openshift-storage")

            # Parse resources

            # Check that the env vars of the depoyment point to the obc/object-review
            deployment_envfrom = {}
            for element in json.loads(str(deployment.spec.template.spec.containers[0].envFrom).replace("'",'"')):
                for key in element:
                    deployment_envfrom[key] = element[key]["name"]

            # List the contents of the S3 bucket
            #
            # Check if we can access the S3 bucket and list the objects
            # (at least one object should exist in the bucket and the prefix "prefix" should exist)
            #
            # This could have been implemented with a boto3 S3 client
            # however I got the following when importing boto3
            #	Could not find module object-review for course do370
            #	Script object-review not in course library do370

            env = os.environ.copy()
            env.pop("LS_COLORS", None)
            env.update(dict(configmap.data))
            secret_data = dict(secret.data)

            for element in secret_data:
                env[element] = base64.b64decode(secret_data[element]).decode()
            env["BUCKET_HOST"] = route.spec.host

            if env["BUCKET_PORT"] == "80":
                env["BUCKET_PROTO"] = "http"
            else:
                env["BUCKET_PROTO"] = "https"

            result = subprocess.run(
                [
                    "{}/.venv/labs/bin/aws".format(os.environ["HOME"]),
                    "s3",
                    "ls",
                    "s3://{}".format(env["BUCKET_NAME"]),
                    "--endpoint-url",
                    "{}://{}:{}".format(env["BUCKET_PROTO"], env["BUCKET_HOST"], env["BUCKET_PORT"]),
                    "--recursive",
                    "--summarize",
                    "--no-verify-ssl",
                ],
                check=True,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            lines = result.stdout.splitlines()[-2]
            last_word = lines.split()[-1]
            num_objects = int(last_word)

            # Check constraints and decide pass/fail
            if (
                    obc.spec.storageClassName == "ocs-storagecluster-ceph-rgw"
                    and
                    deployment_envfrom["configMapRef"] == "object-review"
                    and
                    deployment_envfrom["secretRef"] == "object-review"
                    and
                    route.spec.host == "ocs-storagecluster-cephobjectstore-openshift-storage.apps.ocp4.example.com"
                    and
                    num_objects >= 0
                ):
                item["failed"] = False
            else:
                item["failed"] = True

        except Exception as e:
            exception_name = e.__class__.__name__
            logging.info("Could not get resources")
            item["failed"] = True
            item["msgs"] = [{"text": "Could not get resources"}]
            item["exception"] = {
                "name": exception_name,
                "message": str(e),
            }
        return item["failed"]

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
