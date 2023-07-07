#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_utils import versionutils
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import false
from sqlalchemy.sql import or_

from nova import context as nova_context
from nova.db.sqlalchemy import api as db_api
from nova.db.sqlalchemy import api_models
from nova import exception
from nova import objects
from nova.objects import base
from nova.objects import cell_mapping
from nova.objects import fields


@base.NovaObjectRegistry.register
class InstanceMapping(base.NovaTimestampObject, base.NovaObject):
    # Version 1.0: Initial version
    # Version 1.1: Add queued_for_delete
    # Version 1.2: Add user_id
    VERSION = '1.2'

    fields = {
        'id': fields.IntegerField(read_only=True),
        'instance_uuid': fields.UUIDField(),
        'cell_mapping': fields.ObjectField('CellMapping', nullable=True),
        'project_id': fields.StringField(),
        'user_id': fields.StringField(),
        'queued_for_delete': fields.BooleanField(default=False),
        }

    def obj_make_compatible(self, primitive, target_version):
        super(InstanceMapping, self).obj_make_compatible(primitive,
                                                         target_version)
        target_version = versionutils.convert_version_to_tuple(target_version)
        if target_version < (1, 2) and 'user_id' in primitive:
            del primitive['user_id']
        if target_version < (1, 1):
            if 'queued_for_delete' in primitive:
                del primitive['queued_for_delete']

    def _update_with_cell_id(self, updates):
        cell_mapping_obj = updates.pop("cell_mapping", None)
        if cell_mapping_obj:
            updates["cell_id"] = cell_mapping_obj.id
        return updates

    @staticmethod
    def _get_user_id(context, instance_uuid, cell):
        """Find the instance user_id given an instance UUID.

        :param context: The RequestContext to use for database access
        :param instance_uuid: The UUID of the instance
        :param cell: The CellMapping for the instance (can be None)

        :returns: The instance user_id if found, else None
        """
        user_id = None
        # Try the request spec first.
        try:
            rs = objects.RequestSpec.get_by_instance_uuid(context,
                                                          instance_uuid)
            user_id = rs.user_id
        except exception.RequestSpecNotFound:
            pass
        if user_id is not None:
            return user_id
        # Next, try the build request.
        try:
            br = objects.BuildRequest.get_by_instance_uuid(context,
                                                           instance_uuid)
            user_id = br.instance.user_id
        except exception.BuildRequestNotFound:
            pass
        if user_id is not None:
            return user_id
        # Finally, try to get the instance from the cell (if it has a cell).
        if cell is not None:
            try:
                with nova_context.target_cell(context, cell) as cctxt:
                    inst = objects.Instance.get_by_uuid(cctxt, instance_uuid,
                                                        expected_attrs=[])
                user_id = inst.user_id
            except exception.InstanceNotFound:
                pass
        return user_id

    @staticmethod
    def _from_db_object(context, instance_mapping, db_instance_mapping):
        for key in instance_mapping.fields:
            db_value = db_instance_mapping.get(key)
            if key == 'cell_mapping':
                # cell_mapping can be None indicating that the instance has
                # not been scheduled yet.
                if db_value:
                    db_value = cell_mapping.CellMapping._from_db_object(
                        context, cell_mapping.CellMapping(), db_value)
            if key == 'user_id' and db_value is None:
                # If user_id is NULL, we can't set the field because it's
                # non-nullable. We need instance uuid and/or instance cell in
                # order to populate user_id, so do it after all the other
                # attributes are set.
                continue
            setattr(instance_mapping, key, db_value)
        if 'user_id' not in instance_mapping:
            # NOTE(melwitt): Though the user_id column is nullable, the object
            # field is not. So, find the instance user_id.
            user_id = InstanceMapping._get_user_id(
                context, instance_mapping.instance_uuid,
                instance_mapping.cell_mapping)
            # If we can't find the user_id, raise InstanceMappingNotFound.
            # We don't expect this to happen, but if we can't find the user_id
            # to set the non-nullable field on the object, we can't continue.
            if user_id is not None:
                instance_mapping.user_id = user_id
            else:
                raise exception.InstanceMappingNotFound(
                    uuid=instance_mapping.instance_uuid)
        instance_mapping.obj_reset_changes()
        instance_mapping._context = context
        return instance_mapping

    @staticmethod
    @db_api.api_context_manager.reader
    def _get_by_instance_uuid_from_db(context, instance_uuid):
        db_mapping = (context.session.query(api_models.InstanceMapping)
                        .options(joinedload('cell_mapping'))
                        .filter(
                            api_models.InstanceMapping.instance_uuid
                            == instance_uuid)).first()
        if not db_mapping:
            raise exception.InstanceMappingNotFound(uuid=instance_uuid)

        return db_mapping

    @base.remotable_classmethod
    def get_by_instance_uuid(cls, context, instance_uuid):
        db_mapping = cls._get_by_instance_uuid_from_db(context, instance_uuid)
        return cls._from_db_object(context, cls(), db_mapping)

    @staticmethod
    @db_api.api_context_manager.writer
    def _create_in_db(context, updates):
        db_mapping = api_models.InstanceMapping()
        db_mapping.update(updates)
        db_mapping.save(context.session)
        # NOTE: This is done because a later access will trigger a lazy load
        # outside of the db session so it will fail. We don't lazy load
        # cell_mapping on the object later because we never need an
        # InstanceMapping without the CellMapping.
        db_mapping.cell_mapping
        return db_mapping

    @base.remotable
    def create(self):
        changes = self.obj_get_changes()
        changes = self._update_with_cell_id(changes)
        if 'queued_for_delete' not in changes:
            # NOTE(danms): If we are creating a mapping, it should be
            # not queued_for_delete (unless we are being asked to
            # create one in deleted state for some reason).
            changes['queued_for_delete'] = False
        db_mapping = self._create_in_db(self._context, changes)
        self._from_db_object(self._context, self, db_mapping)

    @staticmethod
    @db_api.api_context_manager.writer
    def _save_in_db(context, instance_uuid, updates):
        db_mapping = context.session.query(
                api_models.InstanceMapping).filter_by(
                        instance_uuid=instance_uuid).first()
        if not db_mapping:
            raise exception.InstanceMappingNotFound(uuid=instance_uuid)

        db_mapping.update(updates)
        # NOTE: This is done because a later access will trigger a lazy load
        # outside of the db session so it will fail. We don't lazy load
        # cell_mapping on the object later because we never need an
        # InstanceMapping without the CellMapping.
        db_mapping.cell_mapping
        context.session.add(db_mapping)
        return db_mapping

    @base.remotable
    def save(self):
        changes = self.obj_get_changes()
        changes = self._update_with_cell_id(changes)
        db_mapping = self._save_in_db(self._context, self.instance_uuid,
                changes)
        self._from_db_object(self._context, self, db_mapping)
        self.obj_reset_changes()

    @staticmethod
    @db_api.api_context_manager.writer
    def _destroy_in_db(context, instance_uuid):
        result = context.session.query(api_models.InstanceMapping).filter_by(
                instance_uuid=instance_uuid).delete()
        if not result:
            raise exception.InstanceMappingNotFound(uuid=instance_uuid)

    @base.remotable
    def destroy(self):
        self._destroy_in_db(self._context, self.instance_uuid)


@db_api.api_context_manager.writer
def populate_queued_for_delete(context, max_count):
    cells = objects.CellMappingList.get_all(context)
    processed = 0
    for cell in cells:
        ims = (
            # Get a direct list of instance mappings for this cell which
            # have not yet received a defined value decision for
            # queued_for_delete
            context.session.query(api_models.InstanceMapping)
            .options(joinedload('cell_mapping'))
            .filter(
                api_models.InstanceMapping.queued_for_delete == None)  # noqa
            .filter(api_models.InstanceMapping.cell_id == cell.id)
            .limit(max_count).all())
        ims_by_inst = {im.instance_uuid: im for im in ims}
        with nova_context.target_cell(context, cell) as cctxt:
            filters = {'uuid': list(ims_by_inst.keys()),
                       'deleted': True,
                       'soft_deleted': True}
            instances = objects.InstanceList.get_by_filters(
                cctxt, filters, expected_attrs=[])
        # Walk through every deleted instance that has a mapping needing
        # to be updated and update it
        for instance in instances:
            im = ims_by_inst.pop(instance.uuid)
            im.queued_for_delete = True
            context.session.add(im)
            processed += 1
        # Any instances we did not just hit must be not-deleted, so
        # update the remaining mappings
        for non_deleted_im in ims_by_inst.values():
            non_deleted_im.queued_for_delete = False
            context.session.add(non_deleted_im)
            processed += 1
        max_count -= len(ims)
        if max_count <= 0:
            break

    return processed, processed


@base.NovaObjectRegistry.register
class InstanceMappingList(base.ObjectListBase, base.NovaObject):
    # Version 1.0: Initial version
    # Version 1.1: Added get_by_cell_id method.
    # Version 1.2: Added get_by_instance_uuids method
    VERSION = '1.2'

    fields = {
        'objects': fields.ListOfObjectsField('InstanceMapping'),
        }

    @staticmethod
    @db_api.api_context_manager.reader
    def _get_by_project_id_from_db(context, project_id):
        return (context.session.query(api_models.InstanceMapping)
                .options(joinedload('cell_mapping'))
                .filter(
                    api_models.InstanceMapping.project_id == project_id)).all()

    @base.remotable_classmethod
    def get_by_project_id(cls, context, project_id):
        db_mappings = cls._get_by_project_id_from_db(context, project_id)

        return base.obj_make_list(context, cls(), objects.InstanceMapping,
                db_mappings)

    @staticmethod
    @db_api.api_context_manager.reader
    def _get_by_cell_id_from_db(context, cell_id):
        return (context.session.query(api_models.InstanceMapping)
                .options(joinedload('cell_mapping'))
                .filter(api_models.InstanceMapping.cell_id == cell_id)).all()

    @base.remotable_classmethod
    def get_by_cell_id(cls, context, cell_id):
        db_mappings = cls._get_by_cell_id_from_db(context, cell_id)
        return base.obj_make_list(context, cls(), objects.InstanceMapping,
                db_mappings)

    @staticmethod
    @db_api.api_context_manager.reader
    def _get_by_instance_uuids_from_db(context, uuids):
        return (context.session.query(api_models.InstanceMapping)
                .options(joinedload('cell_mapping'))
                .filter(api_models.InstanceMapping.instance_uuid.in_(uuids))
                .all())

    @base.remotable_classmethod
    def get_by_instance_uuids(cls, context, uuids):
        db_mappings = cls._get_by_instance_uuids_from_db(context, uuids)
        return base.obj_make_list(context, cls(), objects.InstanceMapping,
                db_mappings)

    @staticmethod
    @db_api.api_context_manager.writer
    def _destroy_bulk_in_db(context, instance_uuids):
        return context.session.query(api_models.InstanceMapping).filter(
                api_models.InstanceMapping.instance_uuid.in_(instance_uuids)).\
                delete(synchronize_session=False)

    @classmethod
    def destroy_bulk(cls, context, instance_uuids):
        return cls._destroy_bulk_in_db(context, instance_uuids)

    @staticmethod
    @db_api.api_context_manager.reader
    def _get_not_deleted_by_cell_and_project_from_db(context, cell_uuid,
                                                     project_id, limit):
        query = context.session.query(api_models.InstanceMapping)
        if project_id is not None:
            # Note that the project_id can be None in case
            # instances are being listed for the all-tenants case.
            query = query.filter_by(project_id=project_id)
        # Both the values NULL (for cases when the online data migration for
        # queued_for_delete was not run) and False (cases when the online
        # data migration for queued_for_delete was run) are assumed to mean
        # that the instance is not queued for deletion.
        query = (query.filter(or_(
            api_models.InstanceMapping.queued_for_delete == false(),
            api_models.InstanceMapping.queued_for_delete.is_(None)))
            .join('cell_mapping')
            .options(joinedload('cell_mapping'))
            .filter(api_models.CellMapping.uuid == cell_uuid))
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_not_deleted_by_cell_and_project(cls, context, cell_uuid,
                                            project_id, limit=None):
        """Return a limit restricted list of InstanceMapping objects which are
        mapped to the specified cell_uuid, belong to the specified
        project_id and are not queued for deletion (note that unlike the other
        InstanceMappingList query methods which return all mappings
        irrespective of whether they are queued for deletion this method
        explicitly queries only for those mappings that are *not* queued for
        deletion as is evident from the naming of the method).
        """
        db_mappings = cls._get_not_deleted_by_cell_and_project_from_db(
            context, cell_uuid, project_id, limit)
        return base.obj_make_list(context, cls(), objects.InstanceMapping,
                db_mappings)
