#!/usr/bin/bash

project_name="volumes-block"

if oc get project ${project_name} &> /dev/null
then
  echo
  echo "Deployment: mysql-no-expand    Pod: $(oc get pods -n ${project_name} -l deployment=mysql-no-expand -o name | cut -d/ -f2)"
  oc exec deployment/mysql-no-expand -n ${project_name} -- /usr/bin/mysql -u root games -t -e 'SELECT YEAR,HOST,TYPE FROM olympics ORDER BY YEAR DESC LIMIT 2;'
  echo
  echo "Deployment: mysql-expand       Pod: $(oc get pods -n ${project_name} -l deployment=mysql-expand -o name | cut -d/ -f2)"
  oc exec deployment/mysql-expand -n ${project_name} -- /usr/bin/mysql -u root fifa -t -e 'SELECT * FROM worldcup ORDER BY YEAR DESC LIMIT 2;'
  echo
else
  echo "ERROR: Project '${project_name}' does not exist." 1>&2
fi
