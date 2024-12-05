#
# Copyright (c) 2020 Red Hat Training <training@redhat.com>
#
# All rights reserved.
# No warranty, explicit or implied, provided.
#
# CHANGELOG
#   * Wed Apr 07, 2021 Michael Phillips <miphilli@redhat.com>
#   - original code

"""
Grading module for DO370: volumes-block
Guided Exercise: Extending Block Storage for an Application
This module provides functions for: start|finish
"""

#########################################################################
#########################################################################
#                   How to use this template:
#
# 1. Rename the file to somethingRelatedToYourLab.py. Use camel case, do not
#    use dashes or underscores.
# 2. Adjust the CHANGELOG and docstring above.
# 3. Define your playbook files in the _playbook_start, _playbook_grade, and
#    _playbook_finish variables below.
# 4. Define the hosts that are used in this activity in the _targets variable.
# 5. Rename the class. The name of the class must match the file name (without
#    the .py extension)
# 6. Remove the methods (start, finish, or grade) that your lab script does
#    not support.
# 7. Remove these "How to use this template" comments
#########################################################################
#########################################################################

from labs.grading import Default
from labs.common import labtools, userinterface

# List of hosts involved in that module. Before doing anything,
# the module checks that they can be reached on the network
_targets = ["localhost", "utility"]
# _targets = ["servera", "serverb"]


# Change the class name to match your file name.
class VolumesBlock(Default):
    """Activity class."""
    __LAB__ = 'volumes-block'

    def start(self):
        """Prepare the system for starting the lab."""
        items = [
            {
                "label": "Checking lab systems",
                "task": labtools.check_host_reachable,
                "hosts": _targets,
                "fatal": True
            },
            #{
            #    "label": "Installing and configuring OpenShift Container Storage",
            #    "task": self.run_playbook,
            #    "playbook": "ansible/install/install-lso-ocs.yml",
            #    "vars": { "max_device_count": "1" },
            #    "fatal": True
            #},
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
                "label": "Labeling nodes for storage",
                "task": self.run_playbook,
                "playbook": "ansible/common/label-nodes.yml",
                "fatal": True
            },
            {
                "label": "Installing and configuring the Local Storage Operator",
                "task": self.run_playbook,
                "playbook": "ansible/common/install-lso.yml",
                "vars": { "max_device_count": "1" },
                "fatal": True
            },
            {
                "label": "Installing and configuring the OpenShift Container Storage operator",
                "task": self.run_playbook,
                "playbook": "ansible/common/install-ocs.yml",
                "fatal": True
            },
            {
                "label": "Adding exercise content",
                "task": self.run_playbook,
                "playbook": "ansible/common/add-exercise-dirs.yml",
                "vars": {"exercise": "{{ exercises['volumes_block'] }}"},
                "fatal": True
            },
            {
                "label": "Configuring exercise applications",
                "task": self.run_playbook,
                "playbook": "ansible/volumes-block/deploy-app.yml",
                "fatal": True
            },
        ]
        userinterface.Console(items).run_items()

    def finish(self):
        """Perform post-lab cleanup."""
        items = [
            {
                "label": "Checking lab systems",
                "task": labtools.check_host_reachable,
                "hosts": _targets,
                "fatal": True
            },
            {
                "label": "Removing exercise namespace",
                "task": self.run_playbook,
                "playbook": "ansible/common/remove-namespace.yml",
                "vars": {"exercise": "{{ volumes_block }}"},
                "fatal": True
            },
            {
                "label": "Removing exercise content",
                "task": self.run_playbook,
                "playbook": "ansible/common/remove-exercise-dirs.yml",
                "vars": {"exercise": "{{ exercises['volumes_block'] }}"},
                "fatal": True
            },
        ]
        userinterface.Console(items).run_items(action="Finishing")
