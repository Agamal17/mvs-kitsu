# -*- coding: utf-8 -*-
import gazu
from ayon_core.lib import get_ffmpeg_tool_path
import os
import subprocess
import pyblish.api


class IntegrateKitsuReview(pyblish.api.InstancePlugin):
    """Integrate Kitsu Review"""

    order = pyblish.api.IntegratorOrder + 0.01
    label = "Kitsu Review"
    families = ["render", "image", "online", "kitsu"]
    optional = True

    def process(self, instance):
        # Check comment has been created
        comment_id = instance.data.get("kitsuComment", {}).get("id")
        if not comment_id:
            self.log.debug(
                "Comment not created, review not pushed to preview."
            )
            return

        kitsu_task = instance.data.get("kitsuTask")
        if not kitsu_task:
            self.log.debug("No kitsu task found, skipping review upload.")
            return

        # Add review representations as preview of comment
        task_id = kitsu_task["id"]
        for representation in instance.data.get("representations", []):
            # Skip if not tagged as review
            if "kitsureview" not in representation.get("tags", []):
                continue
            review_path = representation.get("published_path")
            self.log.debug(f"Found review at: {review_path}")
            if not review_path:
                return

            try:
                gazu.task.add_preview(
                    task=task_id,
                    comment=comment_id,
                    preview_file_path=review_path,
                    normalize_movie=True,
                    revision=instance.data["version"],
                )

            except gazu.exception.TooBigFileException as e:
                self.log.info("Preview is too large, Compressing File...")
                ffmpeg_path = get_ffmpeg_tool_path()
                old_review_path = review_path
                review_path = f"{os.path.splitext(review_path)[0]}_compressed.mp4"
                subprocess.run(
                    [
                        ffmpeg_path,
                        "-i", old_review_path,
                        "-b:v", "50000k",
                        review_path
                    ],
                    check=True
                    )

                gazu.task.add_preview(
                    task=task_id,
                    comment=comment_id,
                    preview_file_path=review_path,
                    normalize_movie=True,
                    revision=instance.data["version"],
                )

            self.log.info("Review upload on comment")
