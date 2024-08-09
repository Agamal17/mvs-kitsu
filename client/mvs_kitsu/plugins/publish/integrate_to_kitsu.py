from copy import deepcopy
import os
if os.environ["AYON_HOST_NAME"] == "hiero":
    from update_kitsu import UpdateZOU
    import pyblish.api
    from ayon_core.pipeline import legacy_io

    class IntegrateAssetToKitsu(pyblish.api.ContextPlugin):

        label = "Integrate Asset To Kitsu"
        order = pyblish.api.IntegratorOrder + 0.2
        families = ["clip", "footage"]
        
        def process(self, context):
            # processing starts here
            if "hierarchyContext" not in context.data:
                self.log.info("skipping IntegrateHierarchyToAvalon")
                return

            if not legacy_io.Session:
                legacy_io.install()

            self.seq_name = ''
            project_name = legacy_io.active_project()
            hierarchy_context = self._get_active_assets(context)
            self.log.warning('self.seq_name')
            self.log.warning(self.seq_name)
            context.data['seq'] = self.seq_name
            self.send_to_zou(context, project_name, hierarchy_context)


        def send_to_zou(self, context, project_name, input_data):
            self.log.debug("__ send_to_zou: project `{}`".format(project_name))
            self.log.debug("__ context `{}`".format(context))
            self.log.debug("__ input_data `{}`".format(input_data))

            creds = {
                "server": context.data["KITSU_SERVER"],
                "user": context.data["KITSU_LOGIN"],
                "password": context.data["KITSU_PWD"] 
            }

            new_shots = {}

            def get_shots(context):
                # get all shots in context
                for k, v in context.items():
                    if isinstance(v, dict):
                        self.log.warning("get Shot")
                        self.log.warning(v)
                        if v.get("entity_type", "").lower() == "shot":
                            new_shots[k] = v
                        get_shots(v)

            get_shots(input_data)
            self.log.debug("__ send_to_zou: new shots {}".format(new_shots))
            self.log.debug("__ anatomyData {}".format(context.data['anatomyData']))

            shot_instances = {x.data['name'].split('_plate')[0].split('_take')[0]: x for x in context}
            self.log.debug("__ shot_instances {}".format(shot_instances))

            for shot_name in new_shots:
                for shot_instance in shot_instances:
                    if (shot_name in shot_instance):
                        frame_in = new_shots[shot_name].get('custom_attributes', {}).get('frameStart', 1001)
                        frame_out = new_shots[shot_name].get('custom_attributes', {}).get('frameEnd', 1200)
                        clipIn = new_shots[shot_name].get('custom_attributes', {}).get('clipIn', 1001)
                        clipOut = new_shots[shot_name].get('custom_attributes', {}).get('clipOut', 1001)
                        handleStart = new_shots[shot_name].get('custom_attributes', {}).get('handleStart', 0)
                        handleEnd = new_shots[shot_name].get('custom_attributes', {}).get('handleEnd', 0)

                        zou_data = {
                            'frame_in': frame_in,
                            'frame_out': frame_out,
                            'clipIn': clipIn,
                            'clipOut': clipOut,
                            'handleStart': handleStart,
                            'handleEnd': handleEnd,
                            'client_name': shot_instances[shot_instance].data['client_name']

                        }
                self.update_zou(shot_name, zou_data, creds)

            for name in input_data:
                self.log.info("input_data[name]: {}".format(input_data[name]))
                entity_data = input_data[name]
                entity_type = entity_data["entity_type"]

                data = {}
                data["entityType"] = entity_type

                # Custom attributes.
                for k, val in entity_data.get("custom_attributes", {}).items():
                    data[k] = val

                self.log.debug("__ shot: {}  -> {}".format(name, entity_type))

                # update to zou
                if entity_type.lower() == "shot":
                    self.log.debug(entity_type)

                    self.log.debug("__ entity type: {}".format(input_data[name]))

                    frame_in = input_data[name].get('custom_attributes').get('frameStart')
                    frame_out = input_data[name].get('custom_attributes').get('frameEnd')
                    clipIn = input_data[name].get('custom_attributes').get('clipIn')
                    clipOut = input_data[name].get('custom_attributes').get('clipOut')
                    handleStart = input_data[name].get('custom_attributes').get('handleStart')
                    handleEnd = input_data[name].get('custom_attributes').get('handleEnd')

                    # Add zou data
                    zou_data = {
                        'frame_in': frame_in,
                        'frame_out': frame_out,
                        'clipIn': clipIn,
                        'clipOut': clipOut,
                        'handleStart': handleStart,
                        'handleEnd': handleEnd,

                    }
                    self.update_zou(name, zou_data, creds)


        def update_zou(self, shot_name, data, creds):
            # updating zou
            zou = UpdateZOU(creds)
            project_name = legacy_io.active_project()

            project = zou.get_zou_project(project_name=project_name)
            self.log.debug("__ project: `{}` ->`{}`".format(project_name, zou.production_type))
            if project is None:
                raise Exception("Wrong `{}` the project is not in kitsu.".format(project_name))

            # Drama
            self.log.debug("__ shot: `{}` ->`{}`".format(shot_name, shot_name.split("_")))
            if zou.production_type == "tvshow":
                ep_name, sh_name = shot_name.split("_")
            else:
                self.log.info(shot_name)
                sh_name = shot_name.split("_")
                ep_name = ""

            zou.create_shot(project, ep_name, self.seq_name, sh_name, task_names=['Conforming'], data=data)

        def _get_active_assets(self, context):
            """ Returns only asset dictionary.
                Usually the last part of deep dictionary which
                is not having any children
            """
            def get_pure_hierarchy_data(input_dict):
                input_dict_copy = deepcopy(input_dict)
                self.log.warning("input dict")
                self.log.warning(input_dict_copy)
                for key in input_dict.keys():
                    self.log.debug("__ key: {}".format(key))
                    # check if child key is available
                    if input_dict[key].get("childs"):
                        if input_dict[key].get("entity_type").lower() == "sequence":
                            self.seq_name = key
                        # loop deeper
                        input_dict_copy[
                            key]["childs"] = get_pure_hierarchy_data(
                                input_dict[key]["childs"])
                    else:
                        for asset in active_assets:
                            if key in asset:
                                break
                        else:
                            self.log.warning("active assets")
                            self.log.warning(active_assets)
                            self.log.warning("input dict in key")
                            self.log.warning(input_dict_copy)
                            input_dict_copy.pop(key, None)
                            self.log.warning("input dict after key pop")
                            self.log.warning(input_dict_copy)
                return input_dict_copy

            hierarchy_context = context.data["hierarchyContext"]

            active_assets = []
            # filter only the active publishing insatnces
            for instance in context:
                if instance.data.get("publish") is False:
                    continue

                if not instance.data.get("asset"):
                    continue

                active_assets.append(instance.data["asset"])

            # remove duplicity in list
            active_assets = list(set(active_assets))
            self.log.debug("__ active_assets: {}".format(active_assets))

            return get_pure_hierarchy_data(hierarchy_context)
