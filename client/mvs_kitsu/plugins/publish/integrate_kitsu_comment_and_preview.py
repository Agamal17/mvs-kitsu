import logging

import pyblish.api
import os

if os.environ["AYON_HOST_NAME"] == "hiero":
    class IntegrateCommentAndPreviewToKitsu(pyblish.api.InstancePlugin):

        label = "Integrate Preview & Comment To Kitsu"
        order = pyblish.api.IntegratorOrder + 0.3
        families = ["clip", "footage"]

        def process(self, instance):
            creds = {
                "server": instance.context.data["KITSU_SERVER"],
                "user": instance.context.data["KITSU_LOGIN"],
                "password": instance.context.data["KITSU_PWD"] 
            }

            if 'clip' in instance.data['families']:
                self.log.debug(f"add clip preview to kitsu")
                self.add_preview_kitsu(instance.data, creds)

            elif 'footage' in instance.data['families']:
                self.log.debug(f"add footage comment to kitsu")
                self.add_comment_kitsu(instance.data, creds)

        def add_comment_kitsu(self, data, creds, task_name='Conforming_PL'):
            if data.get('productType') == 'plate':
                from update_kitsu import UpdateZOU

                sh_name = data.get('asset_name')
                op_plate_name = data.get('name')
                seq_name = data.get('hierarchyData', {}).get('sequence', '')
                project_name = data["projectEntity"]["name"]

                comment_data = {
                    'seq_name': seq_name,
                    'sh_name': sh_name,
                    'task_name': task_name,
                    'status_name': 'wfa',
                    'comment': op_plate_name,
                }

                zou = UpdateZOU(creds, project_name)
                zou.add_comment(comment_data)
                self.log.debug(f"comment to kitsu: Conforming - > wfa -> `{op_plate_name}`")

        def add_preview_kitsu(self, data, creds, task_name='Conforming_PL'):
            transferred = data.get("representations")
            if data.get('productType') == 'plate':
                from update_kitsu import UpdateZOU

                op_shot_name = data.get('asset_name')
                op_plate_name = data.get('name')
                seq_name = data.get('hierarchyData', {}).get('sequence', '')
                project_name = data["projectEntity"]["name"]

                if 'clip' in data.get('families'):
                    mov_file = [x['published_path'] for x in transferred if x['published_path'].endswith('mp4') or x['published_path'].endswith('mov')]
                    if mov_file:
                        mov_file = mov_file[0]

                else:
                    mov_file = transferred[-1]['published_path']

                zou = UpdateZOU(creds, project_name)
                data = {
                    'seq_name': seq_name,
                    'sh_name': op_shot_name,
                    'status_name': 'wfa',
                    'task_name': task_name,
                    'comment': op_plate_name,
                }
                
                if not mov_file:
                    zou.add_comment(data)
                    return
                    
                data['path'] = mov_file
                zou.upload_preview(data, main_preview=True)
