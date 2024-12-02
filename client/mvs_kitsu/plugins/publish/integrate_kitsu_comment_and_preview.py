import logging

import pyblish.api
import os

if os.environ["AYON_HOST_NAME"] == "hiero":
    class IntegrateCommentAndPreviewToKitsu(pyblish.api.InstancePlugin):

        label = "Integrate Preview & Comment To Kitsu"
        order = pyblish.api.IntegratorOrder + 0.3
        families = ["plate", "footage", "ref_edit"]

        def process(self, instance):
            creds = {
                "server": instance.context.data["KITSU_SERVER"],
                "user": instance.context.data["KITSU_LOGIN"],
                "password": instance.context.data["KITSU_PWD"]
            }

            if instance.data['productType'] == 'plate':
                self.log.debug(f"add clip preview to kitsu")
                self.add_preview_kitsu(instance.data, creds)

            elif instance.data['productType'] == 'ref_edit':
                self.log.debug(f"add Edit Reference to kitsu")
                if instance.data['mercury_ref']:
                    self.add_preview_kitsu(instance.data, creds, 'Mercury_Edit')
                else:
                    self.add_preview_kitsu(instance.data, creds, 'Reference_Edit')

            elif instance.data['productType'] == 'footage':
                self.log.debug(f"add footage comment to kitsu")
                self.add_comment_kitsu(instance.data, creds)

        def add_comment_kitsu(self, data, creds, task_name='Conforming_PL'):
            from update_kitsu import UpdateZOU

            sh_name = data["folderEntity"]["name"]
            op_plate_name = f"{data.get('folderPath')}_{data.get('productName')}"
            seq_name = data.get('hierarchyData', {}).get('sequence', '')
            project_name = data["projectEntity"]["name"]

            comment_data = {
                'seq_name': seq_name,
                'sh_name': sh_name,
                'task_name': task_name,
                'comment': op_plate_name,
            }

            zou = UpdateZOU(creds, project_name)
            zou.add_comment(comment_data)
            self.log.debug(f"comment to kitsu: Conforming - > wfa -> `{op_plate_name}`")

        def add_preview_kitsu(self, data, creds, task_name='Conforming_PL'):
            transferred = data.get("representations")
            from update_kitsu import UpdateZOU

            op_shot_name = data["folderEntity"]["name"]
            op_plate_name = f"{data.get('folderPath')}_{data.get('productName')}"
            seq_name = data.get('hierarchyData', {}).get('sequence', '')
            project_name = data["projectEntity"]["name"]

            mov_file = [x['published_path'] for x in transferred if x['published_path'].endswith('mp4') or x['published_path'].endswith('mov')]
            if mov_file:
                mov_file = mov_file[0]

            zou = UpdateZOU(creds, project_name)
            prev_data = {
                'seq_name': seq_name,
                'task_name': task_name,
                'comment': op_plate_name,
                'path': mov_file
            }
            if data['productType'] == 'plate':
                prev_data['sh_name'] = op_shot_name

            zou.upload_preview(prev_data, main_preview=True)
