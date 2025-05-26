import gazu


class UpdateZOU:

    def __init__(self, creds, project_name=None):
        self.production_type = None
        self.zou_login(creds)

        self.project = self.get_zou_project(project_name)

        self.default_tasks = ["Conforming"]

    def zou_login(self, creds):
        gazu.client.set_host(creds['server'])
        gazu.log_in(creds['user'], creds['password'])

    def get_shot(self, sq_name, sh_name, ep_name=None):
        seq = gazu.shot.get_sequence_by_name(self.project, sq_name)
        return gazu.shot.get_shot_by_name(seq, sh_name)

    def get_zou_project(self, project_name):
        project = gazu.project.get_project_by_name(project_name)

        if project:
            self.production_type = project.get('production_type', 'None')
            return project
        else:
            return None

    def create_shot(self, project, seq_name="", sh_name="", task_names=None, data={}):
        sequence = gazu.shot.get_sequence_by_name(project, seq_name)
        if sequence is None:
            sequence = gazu.shot.new_sequence(project, name=seq_name)

        shot = gazu.shot.get_shot_by_name(sequence, sh_name)
        if shot is None:
            if len(seq_name.split("_")) == 3:
                ep_name = seq_name.split("_")[0]
                data['episode'] = f"EP{ep_name[3:]}"

            shot = gazu.shot.new_shot(project,
                                      sequence,
                                      sh_name,
                                      frame_in=data.get('frame_in'),
                                      frame_out=data.get('frame_out'),
                                      nb_frames=int(data.get('frame_out')) - int(data.get('frame_in')) + 1,
                                      data=data
                                      )
            shot['canceled'] = False
            shot['client_name'] = data.get('client_name', '')
            gazu.shot.update_shot(shot)

        # add tasks
        if task_names is None:
            return
        for task_type_name in task_names:
            task_type = gazu.task.get_task_type_by_name(task_type_name)
            if task_type is not None:
                task = gazu.task.new_task(shot, task_type)

        return shot

    def upload_preview(self, data, main_preview=False):
        seq_name = data.get('seq_name')
        sh_name = data.get('sh_name')
        task_name = data.get('task_name')
        path = data.get('path')
        comment_text = data.get('comment')
        status_name = data.get('status', 'wfa')

        sequence = gazu.shot.get_sequence_by_name(self.project, seq_name)
        if sequence is None:
            return

        if sh_name:
            shot = gazu.shot.get_shot_by_name(sequence, sh_name)
            if shot is None:
                return
        else:
            shot = sequence

        task_type = gazu.task.get_task_type_by_name(task_name)
        if task_type is None:
            return

        task = gazu.task.get_task_by_name(shot, task_type)
        if not task:
            task = gazu.task.new_task(shot, task_type)
        status = gazu.task.get_task_status_by_short_name(status_name)
        comment = gazu.task.add_comment(task, status, comment_text)
        if not path:
            return

        try:
            preview_file = gazu.task.add_preview(
                task,
                comment,
                path,
                normalize_movie=True
            )

        except gazu.exception.TooBigFileException as e:
            from ayon_core.lib import get_ffmpeg_tool_path
            import os
            import subprocess

            ffmpeg_path = get_ffmpeg_tool_path()
            old_review_path = path
            path = f"{os.path.splitext(path)[0]}_compressed.mp4"
            subprocess.run(
                [
                    ffmpeg_path,
                    "-i", old_review_path,
                    "-b:v", "50000k",
                    path
                ],
                check=True
            )

            preview_file = gazu.task.add_preview(
                task,
                comment,
                path,
                normalize_movie=True
            )

        if main_preview:
            gazu.task.set_main_preview(preview_file)

    def add_comment(self, data):
        seq_name = data.get('seq_name')
        sh_name = data.get('sh_name')
        asset_name = data.get('asset_name')

        task_type_name = data.get('task_name')
        comment_text = data.get('comment')
        status_name = data.get('status', 'wfa')

        # get shots
        sequence = gazu.shot.get_sequence_by_name(self.project, seq_name)
        shot = None
        if sequence:
            shot = gazu.shot.get_shot_by_name(sequence, sh_name)

        # get assets
        asset = gazu.asset.get_asset_by_name(self.project, asset_name)

        # get status
        task_type = gazu.task.get_task_type_by_name(task_type_name)
        task_status = gazu.task.get_task_status_by_short_name(status_name)

        if asset:
            task = gazu.task.get_task_by_name(asset, task_type)
            if not task:
                task = gazu.task.new_task(asset, task_type)
        elif shot:
            task = gazu.task.get_task_by_name(shot, task_type)
            if not task:
                task = gazu.task.new_task(shot, task_type)
        else:
            return

        comment = gazu.task.add_comment(task, task_status, comment_text)

    def get_descriptor_by_name(self, col_name):
        all_des = gazu.project.all_metadata_descriptors(self.project)
        stage_des = [x for x in all_des if x['name'] == col_name]
        return stage_des

    def add_metadata_column(self, col_name, values=[], _type='Asset'):
        descriptor = self.get_descriptor_by_name(col_name)

        if descriptor:
            self.update_metadata_column(col_name, values)
        else:
            gazu.project.add_metadata_descriptor(self.project, col_name, _type, values)

    def update_metadata_column(self, col_name, values):
        all_des = gazu.project.all_metadata_descriptors(self.project)
        stage_des = [x for x in all_des if x['name'] == col_name]
        if stage_des:
            stage_des = stage_des[0]
        else:
            return

        stage_des['choices'].extend(values)
        stage_des['choices'] = list(set(stage_des['choices']))
        gazu.project.update_metadata_descriptor(self.project, stage_des)

    def set_metadata(self, asset, col_name, value, _type='Shot'):

        if _type == 'Shot':
            gazu.shot.update_shot_data(asset, {col_name: value})
        else:
            gazu.asset.update_asset_data(asset, {col_name: value})

    def add_task_to_sequence(self, project, seq_name, task_name):
        sequence = gazu.shot.get_sequence_by_name(project, seq_name)
        task_type = gazu.task.get_task_type_by_name(task_name)
        if task_type is not None:
            task = gazu.task.new_task(sequence, task_type)


if __name__ == "__main__":
    zou = UpdateZOU("agamal")
    data = {'ep_name': 'ep01', 'seq_name': 'hey', 'sh_name': '/Sequences/hey/sh020',
            'path': '\\\\st\\Productions\\agamal\\Sequences\\hey\\sh020\\publish\\plate\\plateVideo_1\\v001\\agamal_sh020_plateVideo_1_v001.mp4',
            'task_name': 'Conforming', 'comment': '/Sequences/hey/sh020_plateVideo_1'}
    zou.upload_preview(data, main_preview=True)
