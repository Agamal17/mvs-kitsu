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
                self.add_preview_kitsu(instance.data, creds, instance, task_name='Conforming')

            elif 'footage' in instance.data['families']:
                self.log.debug(f"add footage comment to kitsu")
                self.add_comment_kitsu(instance.data, creds, task_name='Conforming')

        def add_comment_kitsu(self, data, creds, task_name='Conforming'):
            if data.get('family') == 'plate':
                from update_kitsu import UpdateZOU

                op_shot_name = data.get('asset')
                op_plate_name = data.get('name')
                ep_name = data.get('hierarchyData', {}).get('episode', '')
                project_name = data["projectEntity"]["name"]

                if len(op_shot_name.split("_")) == 3:
                    ep_name, seq_name, sh_name = op_shot_name.split("_")
                elif len(op_shot_name.split("_")) == 2:
                    seq_name, sh_name = op_shot_name.split("_")
                else:
                    self.log.debug(f"Can not create : `{op_shot_name}` Please check the naming, must be ep##_sq##_sh###")
                    return

                # if ep_name:
                #     # drama
                #     ep_name, seq_name, sh_name = op_shot_name.split("_")
                # else:
                #     ep_name = None
                #     seq_name, sh_name = op_shot_name.split("_")

                comment_data = {
                    'ep_name': ep_name,
                    'seq_name': seq_name,
                    'sh_name': sh_name,
                    'task_name': task_name,
                    'status_name': 'wfa',
                    'comment': op_plate_name,
                }

                zou = UpdateZOU(creds, project_name)
                zou.add_comment(comment_data)
                self.log.debug(f"comment to kitsu: Conforming - > wfa -> `{op_plate_name}`")

        def add_preview_kitsu(self, data, creds, instance, task_name='Conforming'):
            transferred = data.get("representations")
            if data.get('family') == 'plate':
                from update_kitsu import UpdateZOU

                op_shot_name = data.get('asset')
                op_plate_name = data.get('name')
                ep_name = data.get('hierarchyData', {}).get('episode', '')
                project_name = data["projectEntity"]["name"]
                self.log.debug(f"{project_name}")

                if 'clip' in data.get('families'):
                    self.log.debug("clip")
                    self.log.debug(transferred)
                    mov_file = [x['published_path'] for x in transferred if x['published_path'].endswith('mp4') or x['published_path'].endswith('mov')]
                    if mov_file:
                        mov_file = mov_file[0]

                else:
                    mov_file = transferred[-1]['published_path']

                if len(op_shot_name.split("_")) == 2:
                    ep_name, sh_name = op_shot_name.split("_")
                elif len(op_shot_name.split("_")) == 1:
                    sh_name = op_shot_name.split("_")
                else:
                    self.log.debug(f"Can not create : `{op_shot_name}` Please check the naming, must be ep##_sq##_sh###")
                    return

                preview_data = {
                    'ep_name': ep_name,
                    'seq_name': instance.context.data['seq'],
                    'sh_name': sh_name[0].split("/")[-1],
                    'path': mov_file,
                    'task_name': task_name,
                    'comment': op_plate_name,
                }
                zou = UpdateZOU(creds, project_name)
                self.log.debug(f"{preview_data}")

                zou.upload_preview(preview_data, main_preview=True)
