from copy import deepcopy
import os
if os.environ["AYON_HOST_NAME"] == "hiero":
    from update_kitsu import UpdateZOU
    import pyblish.api

    class IntegrateAssetToKitsu(pyblish.api.InstancePlugin):

        label = "Integrate Asset To Kitsu"
        order = pyblish.api.IntegratorOrder + 0.2
        families = ["shot", "ref_edit"]
        
        def process(self, instance):

            creds = {
                "server": instance.context.data["KITSU_SERVER"],
                "user": instance.context.data["KITSU_LOGIN"],
                "password": instance.context.data["KITSU_PWD"]
            }

            if not instance.data['publish']:
                return

            zou = UpdateZOU(creds)
            project_name = os.environ["AYON_PROJECT_NAME"]
            project = zou.get_zou_project(project_name=project_name)
            if project is None:
                raise Exception("Wrong `{}` the project is not in kitsu.".format(project_name))

            if instance.data['productType'] == 'ref_edit':
                sequence = instance.data["folderEntity"]["name"]
                if instance.data['upload_preview']:
                    zou.add_task_to_sequence(project, sequence, 'Mercury_Edit')

            else:
                shot_name = instance.data["folderEntity"]["name"]
                sequence = instance.data.get("hierarchyData")['sequence']
                frame_in = instance.data.get('frameStart', 1001)
                frame_out = instance.data.get('frameEnd', 1200)
                clipIn = instance.data.get('clipIn', 1001)
                clipOut = instance.data.get('clipOut', 1001)
                handleStart = instance.data.get('handleStart', 0)
                handleEnd = instance.data.get('handleEnd', 0)


                zou_data = {
                    'frame_in': frame_in,
                    'frame_out': frame_out,
                    'clipIn': clipIn,
                    'clipOut': clipOut,
                    'handleStart': handleStart,
                    'handleEnd': handleEnd,
                }

                zou.create_shot(project, seq_name=sequence, sh_name=shot_name, task_names=['Conforming_PL'], data=zou_data)
