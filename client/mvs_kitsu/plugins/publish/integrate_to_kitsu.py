from copy import deepcopy
import os
if os.environ["AYON_HOST_NAME"] == "hiero":
    from update_kitsu import UpdateZOU
    import pyblish.api

    class IntegrateAssetToKitsu(pyblish.api.ContextPlugin):

        label = "Integrate Asset To Kitsu"
        order = pyblish.api.IntegratorOrder + 0.2
        families = ["clip", "footage"]
        
        def process(self, context):
            # processing starts here
            if "hierarchyContext" not in context.data:
                self.log.info("skipping IntegrateHierarchyToAvalon")
                return

            hierarchy_context = self._get_active_assets(context)
            self.send_to_zou(context, hierarchy_context)

        def send_to_zou(self, context, input_data):
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
                        if v.get("folder_type", "").lower() == "shot":
                            new_shots[k] = v
                        get_shots(v)

            get_shots(input_data)

            shot_instances = {x.data['name'].split('_plate')[0].split('_take')[0]: x for x in context}

            for shot_name in new_shots:
                for shot_instance in shot_instances:
                    if (shot_name in shot_instance):
                        frame_in = new_shots[shot_name].get('attributes', {}).get('frameStart', 1001)
                        frame_out = new_shots[shot_name].get('attributes', {}).get('frameEnd', 1200)
                        clipIn = new_shots[shot_name].get('attributes', {}).get('clipIn', 1001)
                        clipOut = new_shots[shot_name].get('attributes', {}).get('clipOut', 1001)
                        handleStart = new_shots[shot_name].get('attributes', {}).get('handleStart', 0)
                        handleEnd = new_shots[shot_name].get('attributes', {}).get('handleEnd', 0)
                        sequence = new_shots[shot_name].get("parent")

                        zou_data = {
                            'frame_in': frame_in,
                            'frame_out': frame_out,
                            'clipIn': clipIn,
                            'clipOut': clipOut,
                            'handleStart': handleStart,
                            'handleEnd': handleEnd,
                        }
                        break

                self.update_zou(shot_name, sequence, zou_data, creds)


        def update_zou(self, shot_name, seq_name, data, creds):
            # updating zou
            zou = UpdateZOU(creds)
            project_name = os.environ["AYON_PROJECT_NAME"]

            project = zou.get_zou_project(project_name=project_name)
            if project is None:
                raise Exception("Wrong `{}` the project is not in kitsu.".format(project_name))

            zou.create_shot(project, seq_name=seq_name, sh_name=shot_name, task_names=['Conforming_PL'], data=data)

        def _get_active_assets(self, context):
            """ Returns only asset dictionary.
                Usually the last part of deep dictionary which
                is not having any children
            """
            def get_pure_hierarchy_data(input_dict):
                input_dict_copy = deepcopy(input_dict)
                for key in input_dict.keys():
                    # check if child key is available
                    if input_dict[key].get("children"):
                        # loop deeper
                        input_dict_copy[key]["children"] = get_pure_hierarchy_data(
                                                                input_dict[key]["children"]
                                                            )
                    else:
                        for asset in active_assets:
                            if key in asset['name']:
                                input_dict_copy[key]['parent'] = asset['parent']
                                break
                        else:
                            input_dict_copy.pop(key, None)

                return input_dict_copy

            hierarchy_context = context.data["hierarchyContext"]

            active_assets = []
            # filter only the active publishing insatnces
            for instance in context:
                if instance.data.get("publish") is False:
                    continue

                if not instance.data.get("asset_name"):
                    continue

                if not active_assets:
                    active_assets.append(
                        {"name": instance.data["asset_name"], "parent": instance.data['hierarchyData']['sequence']})
                else:
                    for active_asset in active_assets:
                        if not instance.data['asset_name'] in active_asset['name']:
                            active_assets.append({"name": instance.data["asset_name"], "parent": instance.data['hierarchyData']['sequence']})

            # remove duplicity in list
            self.log.debug("__ active_assets: {}".format(active_assets))

            return get_pure_hierarchy_data(hierarchy_context)
