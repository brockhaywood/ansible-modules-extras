#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: rds_snapshot_copy
short_description: copies an existing rds snapshot
description:
    - copies an existing rds snapshot
    - source snapshot must be in available state
options:
  source_region:
    description:
      - source region
      - not provided then the environment default will be assumed
    required: false
  source_db_snapshot_identifier:
    description:
      - identifier of the source db snapshot
      - must be in the "available" state
      - if the source is in the same region then specify the snapshot id
      - if the source is in a different region then specify the snapshot ARN
    required: true
  target_db_snapshot_identifier:
    description:
      - identifier for the copied snapshot
      - cannot be empty
      - must contain 1-255 alphanumeric characters or hyphens
      - first character must be a letter
      - cannot end with a hypen or contain two consecutive hyphens
    required: true

author: "Brock Haywood (@brockhaywood)"
extends_documentation_fragment:
    - aws
    - ec2
'''

EXAMPLES = '''
# Basic Snapshot Copy
- local_action:
    module: copy_rds_snapshots
    region: us-west-2
    source_region: us-east-1
    source_db_snapshot_identifier: arn:aws:rds:us-east-1:000000:snapshot:my-local-snapshot
    target_db_snapshot_identifier: my-new-snapshot-id
'''

try:
    import boto.rds
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False


def copy_snapshot(module, source_conn, conn, source_db_snapshot_identifier=None, target_db_snapshot_identifier=None):

    if not source_db_snapshot_identifier or not target_db_snapshot_identifier:
        module.fail_json(msg='Source DB Snapshot Id and Target DB Snapshot '
                             'Id must be provided')

    try:
        snapshots = source_conn.get_all_dbsnapshots(snapshot_id=source_db_snapshot_identifier)
    except boto.exception.BotoServerError, e:
        module.fail_json(msg="%s: %s" % (e.error_code, e.error_message))

    if not snapshots:
        module.fail_json(msg="Could not find snapshot with "
                             "identifier %s" % (source_db_snapshot_identifier))

    snapshot = snapshots[0]

    if snapshot.status != 'available':
        module.fail_json(msg="Snapshot not available with identifier "
                             "%s" % (source_db_snapshot_identifier))

    snapshot = conn.copy_dbsnapshot(
        source_snapshot_id=source_db_snapshot_identifier,
        target_snapshot_id=target_db_snapshot_identifier
    )

    module.exit_json(changed=True, snapshot_id=snapshot.id)


def main():

    argument_spec = ec2_argument_spec()
    argument_spec.update(
        dict(
            region=dict(),
            source_region=dict(),
            source_db_snapshot_identifier=dict(required=True),
            target_db_snapshot_identifier=dict(required=True),
        )
    )
    module = AnsibleModule(argument_spec=argument_spec)

    if not HAS_BOTO:
        module.fail_json(msg='boto required for this module')

    source_db_snapshot_identifier = module.params.get('source_db_snapshot_identifier')
    source_region = module.params.get('source_region')
    target_db_snapshot_identifier = module.params.get('target_db_snapshot_identifier')

    # Retrieve any AWS settings from the environment.
    region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module)

    if not region:
        module.fail_json(msg=str("Either region or AWS_REGION or EC2_REGION "
                                 "environment variable or boto config "
                                 "aws_region or ec2_region must be set."))

    try:
        conn = connect_to_aws(boto.rds, region, **aws_connect_kwargs)

        if source_region and source_region != region:
            source_conn = connect_to_aws(boto.rds, source_region, **aws_connect_kwargs)
        else:
            source_conn = conn

        copy_snapshot(
            module=module,
            source_conn=source_conn,
            conn=conn,
            source_db_snapshot_identifier=source_db_snapshot_identifier,
            target_db_snapshot_identifier=target_db_snapshot_identifier
        )

    except boto.exception.BotoServerError, e:
        module.fail_json(msg=e.error_message)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

if __name__ == '__main__':
    main()
