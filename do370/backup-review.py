#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
# Aug 24 2021 Andres Hernandez <andres.hernandez@redhat.com>
#   - original code
# Jun 16 2022 Andres Hernandez <andres.hernandez@redhat.com>
#   - Split start/finish functions to create/delete project separately

"""
Grading module for DO370 backup-review guided exercise.

This module implements the start, grading, and finish actions for the
backup-review guided exercise.
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
NAMESPACE = "backup-review"

disable_warnings(InsecureRequestWarning)

# Change the class name to match your file name
class BackupReview(OpenShift):
    """
    backup-review lab script for DO370
    """
    __LAB__ = "backup-review"

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
                "label": "Remove volumes",
                "task": self._finish_remove_volumes,
                "fatal": False,
            },
            {
                "label": "Remove resources",
                "task": self._finish_remove_resources,
                "resources_file": "resources.yaml",
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
                "label": "Remove volumes",
                "task": self._finish_remove_volumes,
                "fatal": False,
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

    # Create resources from ~/DO370/solutions/backup-review/resources.yaml
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

    def _grade_test(self, item):
        logging.debug("_grade_test()")
        item["msgs"] = []
        try:
            # Check if the PersistentVolumeClaims exist
            pvcs = {
                "postgresql-data": None,
                "postgresql-backup": None,
                "postgresql-data-clone": None,
                "postgresql-data-snapshot": None,
                }

            for pvc in pvcs:
                logging.info("Get {}/{}".format("PersistentVolumeClaim", pvc))
                pvcs[pvc] = self.oc_client.resources.get(
                    api_version="v1",
                    kind="PersistentVolumeClaim",
                ).get(name=pvc, namespace=NAMESPACE)
                pvcs[pvc] = pvcs[pvc].to_dict()

            # Check if the VolumeSnapshot exists
            logging.info("Get {}/{}".format("VolumeSnapshot", "postgresql-data-snapshot"))
            volume_snapshot = self.oc_client.resources.get(
                api_version="snapshot.storage.k8s.io/v1",
                kind="VolumeSnapshot",
            ).get(name="postgresql-data-snapshot", namespace=NAMESPACE)
            volume_snapshot = volume_snapshot.to_dict()

            # Check if the VolumeSnapshotContent exists
            volume_snapshot_content_name = volume_snapshot["status"]["boundVolumeSnapshotContentName"]
            logging.info("Get {}/{}".format("VolumeSnapshotContent", volume_snapshot_content_name))
            volume_snapshot_content = self.oc_client.resources.get(
                api_version="snapshot.storage.k8s.io/v1",
                kind="VolumeSnapshotContent",
            ).get(name=volume_snapshot_content_name, namespace=None)
            volume_snapshot_content = volume_snapshot_content.to_dict()

            # Check if the Deployment exists (and points to the PVCs)
            deployments = {
                "postgresql": None,
                "postgresql-clone": None,
                "postgresql-snapshot": None,
            }

            for deployment in deployments:
                logging.info("Get {}/{}".format("Deployment", deployment))
                deployments[deployment] = self.oc_client.resources.get(
                    api_version="apps/v1",
                    kind="Deployment",
                ).get(name=deployment, namespace=NAMESPACE)
                deployments[deployment] = deployments[deployment].to_dict()

            # Check if the backup job exists
            # Not checking the jobs that alter or insert the database
            logging.info("Get {}/{}".format("Job", "postgresql-backup"))
            job = self.oc_client.resources.get(
                api_version="batch/v1",
                kind="Job",
            ).get(name="postgresql-backup", namespace=NAMESPACE)
            job = job.to_dict()

            # Parse resources

            deployment_pvc = {}
            for deployment in deployments:
                deployment_pvc[deployment] = {}
                for element in deployments[deployment]["spec"]["template"]["spec"]["volumes"]:
                    pvc_attr = element.get("persistentVolumeClaim", None)
                    if pvc_attr:
                        deployment_pvc[deployment]["claimName"] = pvc_attr.get("claimName", None)

            job_pvc = {}
            for element in deployments[deployment]["spec"]["template"]["spec"]["volumes"]:
                pvc_attr = element.get("persistentVolumeClaim", None)
                if pvc_attr:
                    job_pvc["claimName"] = pvc_attr.get("claimName", None)

            # Check constraints and decide pass/fail
            # The check sections are split to help debugging
            check = {
                "pvc": False,
                "deployment": False,
                "volume_snapshot": False,
                "job": False,
            }

            if (
                    pvcs["postgresql-data"]["spec"]["storageClassName"] == "ocs-storagecluster-ceph-rbd"
                    and
                    pvcs["postgresql-backup"]["spec"]["storageClassName"] == "ocs-storagecluster-cephfs"
                    and
                    pvcs["postgresql-data-clone"]["spec"]["storageClassName"] == "ocs-storagecluster-ceph-rbd"
                    and
                    pvcs["postgresql-data-clone"]["spec"]["dataSource"]["kind"] == "PersistentVolumeClaim"
                    and
                    pvcs["postgresql-data-clone"]["spec"]["dataSource"]["name"] == "postgresql-data"
                    and
                    pvcs["postgresql-data-snapshot"]["spec"]["storageClassName"] == "ocs-storagecluster-ceph-rbd"
                    and
                    pvcs["postgresql-data-snapshot"]["spec"]["dataSource"]["kind"] == "VolumeSnapshot"
                    and
                    pvcs["postgresql-data-snapshot"]["spec"]["dataSource"]["name"] == "postgresql-data-snapshot"
                ):
                check["pvc"] = True

            if (
                    deployment_pvc["postgresql"]["claimName"] == "postgresql-data"
                    and
                    deployment_pvc["postgresql-clone"]["claimName"] == "postgresql-data-clone"
                    and
                    deployment_pvc["postgresql-snapshot"]["claimName"] == "postgresql-data-snapshot"
                ):
                check["deployment"] = True

            if (
                    volume_snapshot["spec"]["source"]["persistentVolumeClaimName"] == "postgresql-data-clone"
                ):
                check["volume_snapshot"] = True

            if (
                    job_pvc["claimName"] == "postgresql-data-snapshot"
                ):
                check["job"] = True

            if (
                    check["pvc"]
                    and
                    check["deployment"]
                    and
                    check["volume_snapshot"]
                    and
                    check["job"]
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

    def _finish_remove_volumes(self, item):
        logging.debug("_finish_remove_volumes()")
        lab_name = type(self).__LAB__
        lab_dir = os.path.join(
            pkg_resources.resource_filename(__name__, "materials"),
            "solutions",
            lab_name,
        )
        item["msgs"] = []
        try:

            # Check if the VolumeSnapshot exists
            # The VolumeSnapshot will be deleted when the namespace is deleted
            logging.info("Get {}/{}".format("VolumeSnapshot", "postgresql-data-snapshot"))
            volume_snapshot = self.oc_client.resources.get(
                api_version="snapshot.storage.k8s.io/v1",
                kind="VolumeSnapshot",
            ).get(name="postgresql-data-snapshot", namespace=NAMESPACE)
            volume_snapshot = volume_snapshot.to_dict()

            # Delete VolumeSnapshotContent
            volume_snapshot_content_name = volume_snapshot["status"]["boundVolumeSnapshotContentName"]
            logging.info("Delete {}/{}".format("VolumeSnapshotContent", volume_snapshot_content_name))
            volume_snapshot_content = self.oc_client.resources.get(
                api_version="snapshot.storage.k8s.io/v1",
                kind="VolumeSnapshotContent",
            ).delete(name=volume_snapshot_content_name, namespace=None)
            volume_snapshot_content = volume_snapshot_content.to_dict()

            item["failed"] = False

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
        return item["failed"]

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
                    item["msgs"] = [{"text": "Could not delete resources"}]
                    logging.debug("Could not delete resources")
                    item["exception"] = {
                        "name": exception_name,
                        "message": str(e),
                    }
            item["msgs"].append({"text": "Project"})
        return item["failed"]
